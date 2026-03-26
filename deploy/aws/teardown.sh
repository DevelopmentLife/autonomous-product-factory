#!/usr/bin/env bash
# =============================================================================
# APF — Teardown AWS Stack
#
# Deletes the CloudFormation stack and all associated resources.
# RDS is snapshot-protected; use --force to skip the snapshot prompt.
#
# Usage:
#   ./deploy/aws/teardown.sh [--stack apf] [--region us-east-1] [--force]
# =============================================================================

set -euo pipefail

STACK_NAME="${APF_STACK:-apf}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
FORCE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --stack)   STACK_NAME="$2"; shift 2 ;;
    --region)  REGION="$2";     shift 2 ;;
    --force)   FORCE=true;      shift ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

echo "==> This will DELETE the CloudFormation stack '${STACK_NAME}' in region '${REGION}'."
echo "    All ECS services, ALB, ElastiCache, and EFS will be destroyed."
echo "    RDS will be snapshotted before deletion (unless already deleted)."
echo ""

if [[ "${FORCE}" == "false" ]]; then
  read -rp "    Type the stack name to confirm: " confirm
  if [[ "${confirm}" != "${STACK_NAME}" ]]; then
    echo "Aborted."
    exit 1
  fi
fi

echo "==> Deleting stack '${STACK_NAME}'..."
aws cloudformation delete-stack \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}"

echo "==> Waiting for deletion to complete (this may take 10-15 minutes)..."
aws cloudformation wait stack-delete-complete \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}"

echo "==> Stack deleted."
echo ""
echo "    Note: ECR repositories and SSM parameters are NOT deleted by this script."
echo "    To remove them:"
echo "      aws ecr delete-repository --repository-name apf-orchestrator --force --region ${REGION}"
echo "      aws ssm delete-parameters-by-path --path /${STACK_NAME} --recursive --region ${REGION}"
