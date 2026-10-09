#!/bin/bash
# Bootstrap LocalStack with CivicLens buckets + queue (dev only).
set -euo pipefail

# Create S3 buckets
awslocal s3 mb s3://civic-lens-raw
awslocal s3 mb s3://civic-lens-crops

# Create SQS queue
awslocal sqs create-queue --queue-name civic-lens-jobs

echo "LocalStack initialized: S3 buckets + SQS queue created"
