"""
CryptoShredder — Right-To-Be-Forgotten via CMK deletion.

Crypto shredding:
  Delete the customer's CMK(s) from LocalKMS.  Once the CMK is gone the
  wrapped DEKs stored with every EncryptedRecord are permanently unreadable,
  making the column ciphertext indistinguishable from random bytes even for
  an attacker who retains the full record.

  No S3 / file writes are needed for inaccessibility — key deletion alone
  satisfies the "data gone" requirement.  The RecordStore can optionally
  purge physical records for storage hygiene.
"""

from __future__ import annotations

from colenc.kms import KeyDeletedError, KeyNotFoundError, LocalKMS
from colenc.storage import RecordStore


class CryptoShredder:
    """Delete all CMKs for a customer, rendering their data permanently inaccessible."""

    def __init__(
        self,
        kms: LocalKMS | None = None,
        store: RecordStore | None = None,
    ) -> None:
        self._kms = kms or LocalKMS()
        self._store = store or RecordStore()

    def forget_customer(
        self,
        customer_id: str,
        delete_records: bool = False,
    ) -> dict[str, object]:
        """Crypto-shred all data for *customer_id*.

        Deletes every CMK registered for the customer.  After this call all
        wrapped DEKs for those records become unwrappable.

        Args:
            customer_id: The customer to erase.
            delete_records: Also purge the physical :class:`EncryptedRecord`
                            objects from the :class:`RecordStore`.

        Returns:
            A summary dict with ``customer_id``, ``cmks_deleted``,
            ``records_deleted``, and ``success``.
        """
        cmk_ids = self._kms.list_cmks(customer_id)
        deleted_cmks: list[str] = []
        errors: list[str] = []

        for cmk_id in cmk_ids:
            try:
                self._kms.delete_cmk(cmk_id)
                deleted_cmks.append(cmk_id)
            except (KeyNotFoundError, KeyDeletedError):
                # Already deleted — treat as success.
                deleted_cmks.append(cmk_id)
            except Exception as exc:
                errors.append(f"Failed to delete CMK {cmk_id}: {exc}")

        records_deleted = 0
        if delete_records:
            records_deleted = self._store.delete_all_for_customer(customer_id)

        return {
            "customer_id": customer_id,
            "cmks_deleted": deleted_cmks,
            "records_deleted": records_deleted,
            "success": len(errors) == 0,
            "errors": errors,
        }

    def is_forgotten(self, customer_id: str) -> bool:
        """Return ``True`` if all CMKs for *customer_id* have been deleted."""
        cmk_ids = self._kms.list_cmks(customer_id)
        if not cmk_ids:
            return False  # Never had any CMKs — not a "forgotten" customer.
        # Check whether every CMK is gone from the store.
        return all(
            cmk_id not in self._kms._store  # noqa: SLF001
            for cmk_id in cmk_ids
        )
