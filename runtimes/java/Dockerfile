FROM maven:3.9.9-eclipse-temurin-17 AS build
WORKDIR /build
COPY runtimes/java/pom.xml .
RUN mvn -q dependency:go-offline
COPY runtimes/java/src ./src
RUN mvn -q package
FROM eclipse-temurin:17-jre
RUN mkdir -p /opt/runner /work && chown -R 10001:10001 /work
COPY --from=build /build/target/classes /opt/runner/classes
COPY --from=build /build/target/dependency /opt/runner/lib
USER 10001:10001
ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=65 -Djava.io.tmpdir=/tmp"
ENTRYPOINT ["java","-cp","/opt/runner/classes:/opt/runner/lib/*","lab.graph.Runner"]
