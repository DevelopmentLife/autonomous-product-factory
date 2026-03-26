#!/usr/bin/env bash
# =============================================================================
# APF — AWS Deployment Script
#
# Deploys APF to AWS ECS Fargate using CloudFormation.
# Builds Docker images, pushes to ECR, and updates the ECS task definitions.
#
# Usage:
#   ./deploy/aws/deploy.sh [--env prod|staging] [--region us-east-1] [--stack apf]
#
# Prerequisites:
#   - AWS CLI v2 configured (aws configure, or IAM role on EC2/Cloud9)
#   - Docker installed and running
#   - Permissions: ECR, ECS, CloudFormation, IAM, ELB, VPC, SSM, Logs
#
# First deploy (creates all infrastructure):
#   ./deploy/aws/deploy.sh
#
# Subsequent deploys (update images only — fast):
#   ./deploy/aws/deploy.sh --update-only
# =============================================================================

set -euo pipefail

# --------------------------------------------------------------------------- #
# Defaults — override via flags or environment variables
# --------------------------------------------------------------------------- #
ENV="${APF_ENV:-prod}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
STACK_NAME="${APF_STACK:-apf}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
UPDATE_ONLY=false

# --------------------------------------------------------------------------- #
# Parse flags
# --------------------------------------------------------------------------- #
while [[ $# -gt 0 ]]; do
  case $1 in
    --env)        ENV="$2";        shift 2 ;;
    --region)     REGION="$2";     shift 2 ;;
    --stack)      STACK_NAME="$2"; shift 2 ;;
    --update-only) UPDATE_ONLY=true; shift ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

# --------------------------------------------------------------------------- #
# Resolve AWS account ID
# --------------------------------------------------------------------------- #
echo "==> Checking AWS credentials..."
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
echo "    Account: ${ACCOUNT_ID}  Region: ${REGION}"

ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# --------------------------------------------------------------------------- #
# Services to build and deploy
# --------------------------------------------------------------------------- #
SERVICES=(orchestrator agent-runner artifact-store dashboard github-integration slack-connector)

# --------------------------------------------------------------------------- #
# Step 1: Ensure ECR repos exist
# --------------------------------------------------------------------------- #
echo ""
echo "==> Creating ECR repositories (idempotent)..."
for svc in "${SERVICES[@]}"; do
  repo="apf-${svc}"
  aws ecr describe-repositories --repository-names "${repo}" --region "${REGION}" \
    --query 'repositories[0].repositoryUri' --output text 2>/dev/null || \
  aws ecr create-repository \
    --repository-name "${repo}" \
    --region "${REGION}" \
    --image-scanning-configuration scanOnPush=true \
    --output text --query 'repository.repositoryUri'
  echo "    ${repo} OK"
done

# --------------------------------------------------------------------------- #
# Step 2: Docker login to ECR
# --------------------------------------------------------------------------- #
echo ""
echo "==> Logging in to ECR..."
aws ecr get-login-password --region "${REGION}" | \
  docker login --username AWS --password-stdin "${ECR_REGISTRY}"

# --------------------------------------------------------------------------- #
# Step 3: Build and push images
# --------------------------------------------------------------------------- #
echo ""
echo "==> Building and pushing Docker images..."
GIT_SHA="$(git -C "${REPO_ROOT}" rev-parse --short HEAD 2>/dev/null || echo latest)"

for svc in "${SERVICES[@]}"; do
  svc_dir="${REPO_ROOT}/services/${svc}"
  if [[ ! -d "${svc_dir}" ]]; then
    echo "    SKIP ${svc} (no directory)"
    continue
  fi

  image="${ECR_REGISTRY}/apf-${svc}"
  echo "    Building ${image}:${GIT_SHA} ..."

  docker build \
    --platform linux/amd64 \
    --tag "${image}:${GIT_SHA}" \
    --tag "${image}:latest" \
    "${svc_dir}"

  docker push "${image}:${GIT_SHA}"
  docker push "${image}:latest"
  echo "    Pushed ${image}:${GIT_SHA}"
done

# --------------------------------------------------------------------------- #
# Step 4: Ensure required SSM parameters exist
# --------------------------------------------------------------------------- #
echo ""
echo "==> Checking SSM Parameter Store secrets..."

required_params=(
  "/${STACK_NAME}/APF_SECRET_KEY"
  "/${STACK_NAME}/APF_ADMIN_PASSWORD"
)
optional_params=(
  "/${STACK_NAME}/ANTHROPIC_API_KEY"
  "/${STACK_NAME}/OPENAI_API_KEY"
  "/${STACK_NAME}/GITHUB_APP_ID"
  "/${STACK_NAME}/GITHUB_APP_PRIVATE_KEY"
  "/${STACK_NAME}/GITHUB_WEBHOOK_SECRET"
  "/${STACK_NAME}/GITHUB_DEFAULT_REPO"
  "/${STACK_NAME}/SLACK_BOT_TOKEN"
  "/${STACK_NAME}/SLACK_SIGNING_SECRET"
)

missing=()
for p in "${required_params[@]}"; do
  if ! aws ssm get-parameter --name "${p}" --region "${REGION}" &>/dev/null; then
    missing+=("${p}")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo ""
  echo "ERROR: The following required SSM parameters are missing:"
  for p in "${missing[@]}"; do
    echo "  ${p}"
  done
  echo ""
  echo "Set them with:"
  echo "  aws ssm put-parameter --name /${STACK_NAME}/APF_SECRET_KEY \\"
  echo "    --value \"\$(openssl rand -hex 32)\" --type SecureString --region ${REGION}"
  echo "  aws ssm put-parameter --name /${STACK_NAME}/APF_ADMIN_PASSWORD \\"
  echo "    --value \"yourpassword\" --type SecureString --region ${REGION}"
  echo ""
  echo "Optional (leave blank to disable the feature):"
  for p in "${optional_params[@]}"; do
    echo "  aws ssm put-parameter --name ${p} --value \"\" --type SecureString --region ${REGION}"
  done
  exit 1
fi
echo "    All required SSM parameters present."

# --------------------------------------------------------------------------- #
# Step 5: Deploy / update CloudFormation stack
# --------------------------------------------------------------------------- #
if [[ "${UPDATE_ONLY}" == "false" ]]; then
  echo ""
  echo "==> Deploying CloudFormation stack '${STACK_NAME}'..."
  aws cloudformation deploy \
    --stack-name "${STACK_NAME}" \
    --template-file "${REPO_ROOT}/deploy/aws/cloudformation.yml" \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --region "${REGION}" \
    --parameter-overrides \
        StackName="${STACK_NAME}" \
        EcrRegistry="${ECR_REGISTRY}" \
        ImageTag="${GIT_SHA}" \
    --no-fail-on-empty-changeset

  echo "==> Stack deployed."
fi

# --------------------------------------------------------------------------- #
# Step 6: Force ECS service redeployment with new images
# --------------------------------------------------------------------------- #
echo ""
echo "==> Forcing ECS service redeployment..."
for svc in orchestrator agent-runner artifact-store dashboard; do
  ecs_service="${STACK_NAME}-${svc}"
  aws ecs update-service \
    --cluster "${STACK_NAME}" \
    --service "${ecs_service}" \
    --force-new-deployment \
    --region "${REGION}" \
    --query 'service.deployments[0].status' --output text 2>/dev/null && \
    echo "    ${ecs_service}: redeploying" || \
    echo "    ${ecs_service}: not found (skipped)"
done

# --------------------------------------------------------------------------- #
# Step 7: Print stack outputs
# --------------------------------------------------------------------------- #
echo ""
echo "==> Stack outputs:"
aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table 2>/dev/null || true

echo ""
echo "==> Deploy complete!"
echo "    Dashboard: check the LoadBalancerDNS output above"
echo "    API docs:  http://<LoadBalancerDNS>/docs"
