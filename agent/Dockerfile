FROM rust:1.89-bookworm AS build
WORKDIR /src
COPY Cargo.toml .
COPY src ./src
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=build /src/target/release/alert-rule-manager-agent /usr/local/bin/alert-rule-manager-agent
ENTRYPOINT ["/usr/local/bin/alert-rule-manager-agent"]
