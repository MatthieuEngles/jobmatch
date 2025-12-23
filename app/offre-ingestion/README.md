# Calling France Travail Offres d'Emploi API

## 1. Create an account and application on France Travail.io website, to get your credentials.

Then create your .env file with ```CLIENT_ID``` and ```CLIENT_KEY``` you got.

Create .envrc with ```dotenv``` inside.

Run the command from the same directory
```direnv allow .```

if ```direnv``` is not installed:
```bash
pip install direnv
```

## 2. Create OAuth2 Token

```bash
generate_token.sh
```

And save the token in your environment file

Check it is loaded
```bash
echo TOKEN=${TOKEN}
```

## 3. Request to API

Example request:

```bash
curl -i --compressed \
    "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search?motsCles=data" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Accept: application/json"
```
