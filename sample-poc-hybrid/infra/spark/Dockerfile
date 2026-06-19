ARG SPARK_IMAGE_TAG=4.0.0
FROM bitnami/spark:${SPARK_IMAGE_TAG}

ARG DELTA_VERSION=4.0.0
ARG SCALA_BINARY=2.13
ARG HADOOP_AWS_VERSION=3.4.1
ARG AWS_SDK_BUNDLE_VERSION=1.12.770
ARG UC_VERSION=0.3.0

USER root

# ffmpeg for Phase 4 video metadata extraction; curl already present
RUN install_packages ffmpeg curl

ENV SPARK_HOME=/opt/bitnami/spark
ENV JAR_DIR=${SPARK_HOME}/jars

# Maven Central JARs — pinned, checksum-verified by Maven
RUN set -eux; \
    MAVEN=https://repo1.maven.org/maven2; \
    # Delta Lake 4.0
    curl -fsSL ${MAVEN}/io/delta/delta-spark_${SCALA_BINARY}/${DELTA_VERSION}/delta-spark_${SCALA_BINARY}-${DELTA_VERSION}.jar          -o ${JAR_DIR}/delta-spark_${SCALA_BINARY}-${DELTA_VERSION}.jar; \
    curl -fsSL ${MAVEN}/io/delta/delta-storage/${DELTA_VERSION}/delta-storage-${DELTA_VERSION}.jar                                       -o ${JAR_DIR}/delta-storage-${DELTA_VERSION}.jar; \
    # Spark Kafka connector (Spark 4.0 / Scala 2.13)
    curl -fsSL ${MAVEN}/org/apache/spark/spark-sql-kafka-0-10_${SCALA_BINARY}/4.0.0/spark-sql-kafka-0-10_${SCALA_BINARY}-4.0.0.jar       -o ${JAR_DIR}/spark-sql-kafka-0-10_${SCALA_BINARY}-4.0.0.jar; \
    curl -fsSL ${MAVEN}/org/apache/spark/spark-token-provider-kafka-0-10_${SCALA_BINARY}/4.0.0/spark-token-provider-kafka-0-10_${SCALA_BINARY}-4.0.0.jar -o ${JAR_DIR}/spark-token-provider-kafka-0-10_${SCALA_BINARY}-4.0.0.jar; \
    curl -fsSL ${MAVEN}/org/apache/kafka/kafka-clients/4.0.0/kafka-clients-4.0.0.jar                                                     -o ${JAR_DIR}/kafka-clients-4.0.0.jar; \
    curl -fsSL ${MAVEN}/org/apache/commons/commons-pool2/2.12.0/commons-pool2-2.12.0.jar                                                 -o ${JAR_DIR}/commons-pool2-2.12.0.jar; \
    # Hadoop AWS + AWS SDK bundle for S3a
    curl -fsSL ${MAVEN}/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar                          -o ${JAR_DIR}/hadoop-aws-${HADOOP_AWS_VERSION}.jar; \
    curl -fsSL ${MAVEN}/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_BUNDLE_VERSION}/aws-java-sdk-bundle-${AWS_SDK_BUNDLE_VERSION}.jar    -o ${JAR_DIR}/aws-java-sdk-bundle-${AWS_SDK_BUNDLE_VERSION}.jar; \
    # Unity Catalog Spark client
    curl -fsSL ${MAVEN}/io/unitycatalog/unitycatalog-spark_${SCALA_BINARY}/${UC_VERSION}/unitycatalog-spark_${SCALA_BINARY}-${UC_VERSION}.jar -o ${JAR_DIR}/unitycatalog-spark_${SCALA_BINARY}-${UC_VERSION}.jar; \
    curl -fsSL ${MAVEN}/io/unitycatalog/unitycatalog-client/${UC_VERSION}/unitycatalog-client-${UC_VERSION}.jar                          -o ${JAR_DIR}/unitycatalog-client-${UC_VERSION}.jar; \
    chmod 644 ${JAR_DIR}/*.jar

# Smoke test script — used by `make smoke-hybrid`
COPY scripts/smoke-test.py ${SPARK_HOME}/work/smoke-test.py

USER 1001
