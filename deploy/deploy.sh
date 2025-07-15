#!/bin/bash

# Variables
PROJECT_ID="toolproof-563fe"
REPOSITORY_NAME="docker-repo"
REGION="europe-west2"
IMAGE_NAME="europe-west2-docker.pkg.dev/$PROJECT_ID/$REPOSITORY_NAME/image-tp-lnd:latest"
SERVICE_NAME="service-tp-lnd"
SERVICE_ACCOUNT="backend@$PROJECT_ID.iam.gserviceaccount.com"

# Exit immediately if any command fails
set -e

# Set the Google Cloud project
echo "Setting Google Cloud project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Step 1: Build the Docker image
echo "Step 1: Building Docker image..."
docker build -t $IMAGE_NAME .

# Step 2: Authenticate with Artifact Registry and push the Docker image
echo "Step 2: Pushing Docker image to Google Artifact Registry..."
gcloud auth configure-docker "$REGION-docker.pkg.dev"
docker push $IMAGE_NAME

# Step 3: Deploy the image to Cloud Run
echo "Step 3: Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --region $REGION \
    --service-account $SERVICE_ACCOUNT \
    --allow-unauthenticated \
    --project $PROJECT_ID

echo "✅ Deployment successful! Cloud Run service: $SERVICE_NAME"
