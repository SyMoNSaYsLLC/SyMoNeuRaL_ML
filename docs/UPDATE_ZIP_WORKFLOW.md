# Update Zip Workflow

Put update zips directly in the repository root or in `updates/`.

## Apply one update zip

```bash
./scripts/apply_update_zip.sh ./Some_Update.zip
```

## Apply every update zip

```bash
./scripts/apply_repo_updates.sh
```

Future SyMoNeuRaL update zips should include a top-level `UPDATE.sh` script.
