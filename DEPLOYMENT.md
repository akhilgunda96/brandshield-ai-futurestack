# Publish the Round 2 demo

Publication is not complete. No public project URL or repository URL has been created by this package.

## 1. Publish the source repository

Create a repository named `brandshield-ai` in your GitHub account. Upload the contents of this source folder to the repository root, including `.streamlit/`, `.github/`, `.gitignore`, `requirements.txt` and `render.yaml`. Do not upload a populated database, your local `data/` folder or `.venv/`.

You can upload files through GitHub or run these commands inside this source folder after creating an empty remote repository:

```bash
git init -b main
git add .
git commit -m "Prepare BrandShield Round 2 build"
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

Replace `YOUR_REPOSITORY_URL` with the URL GitHub gives you. Use your own GitHub sign-in; do not paste access tokens into project files. Keep the repository accessible to the judges.

## 2. Deploy a Python web service

The included `render.yaml` is a free-demo configuration. In Render, create a Blueprint using the published repository, inspect its plan and settings, and deploy. Alternatively, create a Python Web Service with these settings:

| Setting | Value |
| --- | --- |
| Root directory | Repository root |
| Build command | `python -m pip install -r requirements.txt` |
| Start command | `python launch.py` |
| Health check | `/_stcore/health` |
| Python version | `3.11.13` |
| `BRANDSHIELD_DEMO_MODE` | `true` |
| `BRANDSHIELD_DB` | `data/brandshield.sqlite3` |

The launcher binds to `0.0.0.0` and the host-provided `PORT`. Demo mode creates fictional sample accounts and reviews only when there are no accounts in the database. It does not replace an existing workspace.

Only use fictional content on this shared demo. The sample passwords are public, and judge sessions share the same database. Use a unique review title for each run.

## Storage and availability

Render's free web service uses an ephemeral filesystem: SQLite history can be lost after restart, redeploy or spin-down. The demo can rebuild its sample accounts, but it cannot restore judge-created reviews after that loss. Free services also sleep after inactivity and can show a startup/loading page on the next visit. Do not present this configuration as durable production hosting.

For retained history, choose hosting with persistent storage and set `BRANDSHIELD_DB` to a path on that storage. Review costs and access settings yourself before enabling a paid service. Managed storage and multi-workspace isolation are planned Round 3 work.

Official documentation checked during preparation:

- https://render.com/docs/web-services
- https://render.com/docs/free
- https://render.com/docs/disks

## 3. Verify the published app

1. Open the real hosted URL in a private browser session.
2. Sign in as `creator` with `BrandShield!2026`.
3. Choose EcoVolt, load an example, create a review, inspect evidence and save a revision.
4. Submit for approval, sign out, and sign in as `reviewer` with the same password.
5. Enter a decision reason and approve or request changes.
6. Inspect the revision history and export the JSON report.
7. Repeat a quick check with NovaWear. Verify its findings cite NovaWear sources.
8. Refresh the browser and confirm the review persists within the current running instance.
9. Check the source repository is accessible to a judge.

If the deployed site shows administrator setup rather than the sign-in screen, check that demo mode is enabled and the launcher was used.

## 4. Finish the submission

Replace the pending-link entries in `SUBMISSION_ANSWERS.md` and the project PDF with the actual verified URLs. Upload the updated PDF and use the prepared feature, technology, changes and Round 3 text. The form itself was not submitted during preparation.
