# PowerShell helper to build and deploy to Cloud Run
gcloud builds submit --tag gcr.io/finivo-ai-prod/finivo-backend
gcloud run deploy finivo-backend `
  --image gcr.io/finivo-ai-prod/finivo-backend `
  --platform managed `
  --region asia-south1 `
  --allow-unauthenticated `
  --memory 1Gi `
  --set-env-vars "PLAID_ENV=sandbox,DEBUG=false,ADMIN_MODE=false,RUN_EXTERNAL_TESTS=0"
