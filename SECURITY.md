# Security Policy

## Credential Management

This project has been carefully designed to protect sensitive credentials:

### No Hardcoded Credentials
- All device IDs and product keys are loaded from environment variables
- No credentials are stored in source code
- Configuration uses `os.getenv()` exclusively for sensitive data

### Environment Variables
- Credentials are stored in `.env` file (not tracked by git)
- `.env.example` provides a template without real values
- Required environment variables:
  - `FRENZ_ID`: Your FRENZ device ID
  - `FRENZ_KEY`: Your FRENZ product key

### Git Security
The `.gitignore` file excludes:
- All `.env` files and variants
- Data directories containing recordings
- Log files that might contain sensitive information
- Session data and HDF5 files

### Verification
Before committing, verify no credentials are exposed:
```bash
# Check for hardcoded keys
grep -r "FRENZ_KEY\|PRODUCT_KEY" . --exclude-dir=.git --exclude-dir=.venv

# Verify no .env files will be committed
git status --ignored
```

## Data Privacy

### Local Storage Only
- All data is stored locally on your machine
- No automatic cloud uploads or external transmissions
- Session data remains in the `data/` directory

### Session Data
- Each session is stored in a separate timestamped directory
- Data files are excluded from version control
- Manual export required for sharing data

## Best Practices

1. **Never commit `.env` files**
   - Always use `.env.example` as a template
   - Keep actual credentials in local `.env` only

2. **Review before committing**
   - Check `git diff` for any credential exposure
   - Use `git status` to verify only intended files are staged

3. **Rotate credentials regularly**
   - Update device credentials periodically
   - Remove old session data when no longer needed

4. **Secure your local environment**
   - Restrict file permissions on `.env`
   - Use encrypted storage for sensitive data

## Reporting Security Issues

If you discover a security vulnerability, please:
1. Do NOT create a public issue
2. Contact the maintainers directly
3. Provide details about the vulnerability
4. Allow time for a fix before public disclosure

## Compliance

This project follows security best practices for:
- Environment variable management
- Credential storage
- Data privacy
- Version control safety