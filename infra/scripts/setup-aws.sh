#!/bin/bash
# Provision real AWS resources for CivicLens (S3, DynamoDB, SQS).
# Usage: AWS_REGION=us-east-1 ./infra/scripts/setup-aws.sh
set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"

# S3 Buckets
aws s3 mb "s3://civic-lens-raw" --region "$REGION"
aws s3 mb "s3://civic-lens-crops" --region "$REGION"

# Enable SSE-S3 encryption
aws s3api put-bucket-encryption --bucket civic-lens-raw \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-bucket-encryption --bucket civic-lens-crops \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# S3 lifecycle: raw bucket expires in 14 days
aws s3api put-bucket-lifecycle-configuration --bucket civic-lens-raw \
  --lifecycle-configuration '{
    "Rules": [{"ID":"expire-raw","Status":"Enabled","Expiration":{"Days":14},"Filter":{"Prefix":""}}]
  }'

# DynamoDB tables
aws dynamodb create-table --table-name cl-detections \
  --attribute-definitions \
    AttributeName=det_id,AttributeType=S \
    AttributeName=job_id,AttributeType=S \
  --key-schema AttributeName=det_id,KeyType=HASH \
  --global-secondary-indexes \
  '[{"IndexName":"job-index","KeySchema":[{"AttributeName":"job_id","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"}}]' \
  --billing-mode PAY_PER_REQUEST --region "$REGION"

aws dynamodb create-table --table-name cl-tickets \
  --attribute-definitions \
    AttributeName=ticket_id,AttributeType=S \
    AttributeName=status,AttributeType=S \
    AttributeName=severity,AttributeType=N \
  --key-schema AttributeName=ticket_id,KeyType=HASH \
  --global-secondary-indexes \
  '[{"IndexName":"status-severity-index","KeySchema":[{"AttributeName":"status","KeyType":"HASH"},{"AttributeName":"severity","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}]' \
  --billing-mode PAY_PER_REQUEST --region "$REGION"

aws dynamodb create-table --table-name cl-jobs \
  --attribute-definitions AttributeName=job_id,AttributeType=S \
  --key-schema AttributeName=job_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST --region "$REGION"

# DynamoDB TTL on detections (90 days)
aws dynamodb update-time-to-live --table-name cl-detections \
  --time-to-live-specification "Enabled=true,AttributeName=ttl"

# SQS queue
aws sqs create-queue --queue-name civic-lens-jobs --region "$REGION"

echo "AWS resources created in $REGION"
