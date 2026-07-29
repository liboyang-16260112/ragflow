#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
ENV_FILE="${SCRIPT_DIR}/.env"

SERVICE="${RAGFLOW_SERVICE:-ragflow-cpu}"
WITH_DEPS="${WITH_DEPS:-0}"
PULL_POLICY="${PULL_POLICY:-never}"
BUILD_PROXY="${BUILD_PROXY:-http://172.30.4.37:7897}"
NEED_MIRROR="${NEED_MIRROR:-1}"
RAGFLOW_VERSION="${RAGFLOW_VERSION:-fmoss-$(date +%Y%m%d-%H%M%S)}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-120}"

usage() {
  cat <<'EOF'
Usage: ./docker/rebuild-ragflow.sh [SERVICE] [--with-deps] [--pull]

For ragflow-cpu and ragflow-gpu, build the application image, verify that local
development config is absent, recreate the application service, and wait for
HTTP readiness. For any other Compose service, only start that service.

Options:
  --with-deps  Also start/recreate the selected service's dependencies.
  --pull       Pull the selected service image if it is missing locally.
  -h, --help   Show this help.

Environment overrides:
  BUILD_PROXY, RAGFLOW_IMAGE, RAGFLOW_VERSION, NEED_MIRROR, PULL_POLICY,
  WAIT_TIMEOUT, MINIO_BUCKET
Examples:
  ./docker/rebuild-ragflow.sh ragflow-cpu
  ./docker/rebuild-ragflow.sh ragflow-gpu
  ./docker/rebuild-ragflow.sh es01
  ./docker/rebuild-ragflow.sh es01 --pull
  ./docker/rebuild-ragflow.sh mysql
EOF
}

while (($#)); do
  case "$1" in
    --with-deps)
      WITH_DEPS=1
      ;;
    --pull)
      PULL_POLICY=missing
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      SERVICE="$1"
      ;;
  esac
  shift
done

if [[ "${SERVICE}" == "ragflow-cpu" || "${SERVICE}" == "ragflow-gpu" ]]; then
  IS_RAGFLOW_SERVICE=1
  SERVICE_PROFILE="${SERVICE#ragflow-}"
else
  IS_RAGFLOW_SERVICE=0
  SERVICE_PROFILE=""
fi

if [[ "${SERVICE}" == "ragflow-cpu" ]]; then
  ALTERNATE_SERVICE="ragflow-gpu"
else
  ALTERNATE_SERVICE="ragflow-cpu"
fi

if [[ ! "${WAIT_TIMEOUT}" =~ ^[0-9]+$ ]] || (( WAIT_TIMEOUT < 1 )); then
  echo "WAIT_TIMEOUT must be a positive integer." >&2
  exit 2
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing Compose environment file: ${ENV_FILE}" >&2
  exit 1
fi

IMAGE="${RAGFLOW_IMAGE:-$(sed -n 's/^RAGFLOW_IMAGE=//p' "${ENV_FILE}" | tail -n 1 | tr -d '\r')}"
IMAGE="${IMAGE:-fmoss-ragflow:local}"

compose() {
  RAGFLOW_IMAGE="${IMAGE}" docker compose \
    --env-file "${ENV_FILE}" \
    -f "${COMPOSE_FILE}" \
    --profile "${SERVICE_PROFILE}" \
    "$@"
}

compose_all_app_profiles() {
  RAGFLOW_IMAGE="${IMAGE}" docker compose \
    --env-file "${ENV_FILE}" \
    -f "${COMPOSE_FILE}" \
    --profile cpu \
    --profile gpu \
    "$@"
}

compose_all_profiles() {
  RAGFLOW_IMAGE="${IMAGE}" docker compose \
    --env-file "${ENV_FILE}" \
    -f "${COMPOSE_FILE}" \
    --profile '*' \
    "$@"
}

read_env_value() {
  local key="$1"
  local value

  value="$(sed -n "s/^${key}=//p" "${ENV_FILE}" | tail -n 1 | tr -d '\r')"
  if (( ${#value} >= 2 )) && \
    { [[ "${value:0:1}" == '"' && "${value: -1}" == '"' ]] || \
      [[ "${value:0:1}" == "'" && "${value: -1}" == "'" ]]; }; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "${value}"
}

ensure_minio_bucket() {
  local storage_impl_value
  local minio_bucket_value

  storage_impl_value="${STORAGE_IMPL:-$(read_env_value STORAGE_IMPL)}"
  storage_impl_value="${storage_impl_value:-MINIO}"
  if [[ "${storage_impl_value^^}" != "MINIO" ]]; then
    echo "Storage backend is ${storage_impl_value}; skipping MinIO bucket initialization."
    return
  fi

  minio_bucket_value="${MINIO_BUCKET:-$(read_env_value MINIO_BUCKET)}"
  if [[ -z "${minio_bucket_value}" ]]; then
    echo "MINIO_BUCKET is empty; using multi-bucket mode and skipping bucket initialization."
    return
  fi

  echo "Ensuring MinIO bucket ${minio_bucket_value} exists..."
  compose_all_app_profiles run --rm --no-deps --entrypoint python \
    -e "MINIO_BUCKET=${minio_bucket_value}" \
    -e "WAIT_TIMEOUT=${WAIT_TIMEOUT}" \
    ragflow-cpu -c '
import os
import ssl
import sys
import time

import urllib3
from minio import Minio


def enabled(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes"}


bucket = os.environ["MINIO_BUCKET"].strip()
host = os.environ.get("MINIO_HOST", "minio").strip()
secure = enabled(os.environ.get("MINIO_SECURE", "false"))
if host.startswith("https://"):
    secure = True
    host = host.removeprefix("https://")
elif host.startswith("http://"):
    host = host.removeprefix("http://")

if ":" not in host:
    port = os.environ.get("MINIO_PORT", "9000")
    host = f"{host}:{port}"

verify = enabled(os.environ.get("MINIO_VERIFY", "true"))
http_client = urllib3.PoolManager(
    cert_reqs=ssl.CERT_REQUIRED if verify else ssl.CERT_NONE,
    timeout=urllib3.Timeout(connect=5, read=10),
    retries=False,
)
client = Minio(
    host,
    access_key=os.environ["MINIO_USER"],
    secret_key=os.environ["MINIO_PASSWORD"],
    secure=secure,
    region=os.environ.get("MINIO_REGION") or None,
    http_client=http_client,
)

deadline = time.monotonic() + int(os.environ.get("WAIT_TIMEOUT", "120"))
while True:
    try:
        if client.bucket_exists(bucket):
            print(f"MinIO bucket already exists: {bucket}")
        else:
            client.make_bucket(bucket)
            print(f"Created MinIO bucket: {bucket}")
        break
    except Exception as exc:
        if time.monotonic() >= deadline:
            raise
        print(f"MinIO is not ready ({exc}); retrying...", file=sys.stderr)
        time.sleep(3)
'
}

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required." >&2
  exit 1
fi

compose_services="$(compose_all_profiles config --services)"
if ! grep -Fxq "${SERVICE}" <<<"${compose_services}"; then
  echo "Unknown Compose service: ${SERVICE}" >&2
  echo "Available services:" >&2
  sed 's/^/  /' <<<"${compose_services}" >&2
  exit 2
fi

if [[ "${IS_RAGFLOW_SERVICE}" != "1" ]]; then
  echo "Starting Compose service ${SERVICE} without rebuilding the RAGFlow image..."
  service_up_args=(-d --pull "${PULL_POLICY}")
  if [[ "${WITH_DEPS}" != "1" ]]; then
    service_up_args+=(--no-deps)
  fi
  compose_all_profiles up "${service_up_args[@]}" "${SERVICE}"

  container_id="$(compose_all_profiles ps -q --all "${SERVICE}")"
  if [[ -z "${container_id}" ]]; then
    echo "Compose did not return a container for ${SERVICE}." >&2
    exit 1
  fi

  deadline=$((SECONDS + WAIT_TIMEOUT))
  while (( SECONDS < deadline )); do
    state="$(docker inspect --format '{{.State.Status}}' "${container_id}")"
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${container_id}")"

    if [[ "${state}" == "running" && ( "${health}" == "healthy" || "${health}" == "none" ) ]]; then
      echo "${SERVICE} is ready (container: ${container_id:0:12}, health: ${health})."
      exit 0
    fi

    if [[ "${state}" == "exited" || "${state}" == "dead" ]]; then
      echo "${SERVICE} stopped before becoming ready. Recent logs:" >&2
      compose_all_profiles logs --tail 120 "${SERVICE}" >&2
      exit 1
    fi

    sleep 3
  done

  echo "Timed out waiting for ${SERVICE}. Recent logs:" >&2
  compose_all_profiles logs --tail 120 "${SERVICE}" >&2
  exit 1
fi

build_args=(
  --pull=false
  --network=host
  --build-arg "NEED_MIRROR=${NEED_MIRROR}"
  --build-arg "RAGFLOW_VERSION=${RAGFLOW_VERSION}"
)

if [[ -n "${BUILD_PROXY}" ]]; then
  build_args+=(
    --build-arg "HTTP_PROXY=${BUILD_PROXY}"
    --build-arg "HTTPS_PROXY=${BUILD_PROXY}"
    --build-arg "http_proxy=${BUILD_PROXY}"
    --build-arg "https_proxy=${BUILD_PROXY}"
    --build-arg "NO_PROXY=127.0.0.1,localhost,172.30.0.0/16,mirrors.aliyun.com"
  )
fi

echo "Building ${IMAGE} (version: ${RAGFLOW_VERSION})..."
docker build \
  "${build_args[@]}" \
  -f "${REPO_ROOT}/Dockerfile" \
  -t "${IMAGE}" \
  "${REPO_ROOT}"

echo "Verifying that local development config is absent from the image..."
if ! docker run --rm --entrypoint sh "${IMAGE}" \
  -c 'test ! -e /ragflow/conf/local.service_conf.yaml'; then
  echo "Refusing to deploy: conf/local.service_conf.yaml is present in ${IMAGE}." >&2
  exit 1
fi

ensure_minio_bucket

echo "Recreating Compose service ${SERVICE}..."
alternate_container_id="$(compose_all_app_profiles ps -q --all "${ALTERNATE_SERVICE}")"
if [[ -n "${alternate_container_id}" ]] && \
  [[ "$(docker inspect --format '{{.State.Running}}' "${alternate_container_id}")" == "true" ]]; then
  echo "Stopping alternate application service ${ALTERNATE_SERVICE} to avoid port conflicts..."
  compose_all_app_profiles stop "${ALTERNATE_SERVICE}"
fi

up_args=(-d --force-recreate --pull never)
if [[ "${WITH_DEPS}" != "1" ]]; then
  up_args+=(--no-deps)
fi
compose up "${up_args[@]}" "${SERVICE}"

container_id="$(compose ps -q "${SERVICE}")"
if [[ -z "${container_id}" ]]; then
  echo "Compose did not return a container for ${SERVICE}." >&2
  exit 1
fi

deadline=$((SECONDS + WAIT_TIMEOUT))
while (( SECONDS < deadline )); do
  state="$(docker inspect --format '{{.State.Status}}' "${container_id}")"
  restart_count="$(docker inspect --format '{{.RestartCount}}' "${container_id}")"

  if [[ "${state}" == "running" ]]; then
    published_port="$(docker port "${container_id}" 80/tcp 2>/dev/null | sed -n '1{s/.*://;p;}')"
    if [[ -z "${published_port}" ]] || ! command -v curl >/dev/null 2>&1; then
      echo "${SERVICE} is running (container: ${container_id:0:12}, restarts: ${restart_count})."
      exit 0
    fi

    if curl --fail --silent --show-error --max-time 5 \
      "http://127.0.0.1:${published_port}/" >/dev/null; then
      echo "Deployment succeeded: http://127.0.0.1:${published_port}/ (restarts: ${restart_count})"
      exit 0
    fi
  fi

  sleep 3
done

echo "Timed out waiting for ${SERVICE}. Recent logs:" >&2
compose logs --tail 120 "${SERVICE}" >&2
exit 1
