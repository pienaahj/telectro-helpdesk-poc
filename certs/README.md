# Production certificate files

This directory is a placeholder for production certificate material on the server.

Do not commit real certificate files or private keys.

Expected production material may include:

- certificate file
- private key file
- chain/intermediate certificate file

Examples of possible names:

- `production.crt`
- `production.key`
- `chain.crt`
- `fullchain.pem`
- `privkey.pem`

The actual file names must match the Traefik dynamic TLS configuration used on the production server.

Rules:

- private keys stay out of Git
- certificate files are placed on the production server only
- file permissions must be restricted
- certificate expiry and renewal owner must be documented

