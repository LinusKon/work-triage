Replace the deploy script's API key: move it to the secret manager and deploy. Inspect variable names only; key creation and revocation belong to the user, and the repository and logs must contain no secret values.

1. Find every place the key's variable name is used (names only, no values).
2. Create the new key.
3. Wire the secret-manager reference into the deploy script.
4. Review row 3.
5. Delete the old `.env` file and revoke the old key.
6. Deploy.
7. Verify the deployment and that no value is in the repository or the logs.

keep the step numbers; do not merge or split steps
