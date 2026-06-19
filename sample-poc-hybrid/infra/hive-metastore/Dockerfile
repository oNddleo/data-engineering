FROM apache/hive:4.0.0

USER root

ENV HIVE_HOME=/opt/hive
ENV HADOOP_HOME=/opt/hadoop

# Postgres JDBC driver + AWS SDK jars so the metastore can talk to its
# Postgres backend AND register S3a table locations from MinIO.
ARG POSTGRES_JDBC=42.7.4
ARG HADOOP_AWS=3.4.1
ARG AWS_SDK_BUNDLE=1.12.770

RUN set -eux; \
    MAVEN=https://repo1.maven.org/maven2; \
    curl -fsSL "${MAVEN}/org/postgresql/postgresql/${POSTGRES_JDBC}/postgresql-${POSTGRES_JDBC}.jar"               -o "${HIVE_HOME}/lib/postgresql-${POSTGRES_JDBC}.jar"; \
    curl -fsSL "${MAVEN}/org/apache/hadoop/hadoop-aws/${HADOOP_AWS}/hadoop-aws-${HADOOP_AWS}.jar"                  -o "${HIVE_HOME}/lib/hadoop-aws-${HADOOP_AWS}.jar"; \
    curl -fsSL "${MAVEN}/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_BUNDLE}/aws-java-sdk-bundle-${AWS_SDK_BUNDLE}.jar" -o "${HIVE_HOME}/lib/aws-java-sdk-bundle-${AWS_SDK_BUNDLE}.jar"

USER hive
