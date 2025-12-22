TOKEN=$(curl -s -X POST \
  "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_KEY}" \
  -d "scope=api_offresdemploiv2 o2dsoffre" \
  | jq -r '.access_token')

echo "Token: ${TOKEN}"
