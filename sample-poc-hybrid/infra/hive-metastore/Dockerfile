# Postgres JDBC driver + AWS SDK jars so the metastore can talk to its
# Postgres backend AND register S3a table locations from MinIO.
ARG POSTGRES_JDBC=42.7.4
ARG HADOOP_AWS=3.4.1
ARG AWS_SDK_BUNDLE=1.12.770

# The apache/hive base image ships without curl/wget, so download the jars in a
# dedicated stage that has curl, then copy them into the metastore image.
FROM curlimages/curl:8.11.0 AS jars
ARG POSTGRES_JDBC
ARG HADOOP_AWS
ARG AWS_SDK_BUNDLE
RUN set -eux; \
    MAVEN=https://repo1.maven.org/maven2; \
    mkdir -p /tmp/jars; \
    curl -fsSL "${MAVEN}/org/postgresql/postgresql/${POSTGRES_JDBC}/postgresql-${POSTGRES_JDBC}.jar"               -o "/tmp/jars/postgresql-${POSTGRES_JDBC}.jar"; \
    curl -fsSL "${MAVEN}/org/apache/hadoop/hadoop-aws/${HADOOP_AWS}/hadoop-aws-${HADOOP_AWS}.jar"                  -o "/tmp/jars/hadoop-aws-${HADOOP_AWS}.jar"; \
    curl -fsSL "${MAVEN}/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_BUNDLE}/aws-java-sdk-bundle-${AWS_SDK_BUNDLE}.jar" -o "/tmp/jars/aws-java-sdk-bundle-${AWS_SDK_BUNDLE}.jar"

FROM apache/hive:4.0.0

USER root

ENV HIVE_HOME=/opt/hive
ENV HADOOP_HOME=/opt/hadoop

COPY --from=jars /tmp/jars/ ${HIVE_HOME}/lib/

USER hive
