# Publish to GitHub / GitHub 发布指南

The repository-ready ZIP in this project can be uploaded to an **empty new repository** such as `Irene-SQ/feko-pec-mesh-repair`. The profile URL `https://github.com/Irene-SQ` is an account page, not a repository destination. Creating a repository or pushing changes requires your authenticated GitHub account.

## Method A: GitHub website (no terminal)

1. Sign in to GitHub, click **New repository** from the `+` menu.
2. Owner: `Irene-SQ` (verify account); name: `feko-pec-mesh-repair`.
3. Choose **Public** or **Private** as you prefer.
4. For simplicity, do **not** add GitHub's starter README/.gitignore; these files are already in the package.
5. Create the repository. Open its root, choose **Add file → Upload files**.
6. Upload the **contents of the extracted `feko-pec-mesh-repair/` directory**, preserving folders `assets/`, `docs/`, `references/`, `scripts/`, `tests/`, `agents/`. If browser folder upload does not preserve structure, use Method B.
7. Commit with message `Add FEKO PEC mesh repair skill and illustrated guide`.
8. Confirm screenshots render in `README.md`, and select a suitable license if you intend others to reuse the code. Leave proprietary aircraft models and FEKO projects out of the repository.

## Method B: Git CLI on Windows (recommended)

Run commands **inside the extracted `feko-pec-mesh-repair` directory**:

```powershell
cd "D:\path\to\feko-pec-mesh-repair"
git init -b main
git add .
git commit -m "Add FEKO PEC mesh repair skill and illustrated guide"
git remote add origin https://github.com/Irene-SQ/feko-pec-mesh-repair.git
git push -u origin main
```

The repository must already exist and your Git credentials must be authorized. If the target repository is **not empty**, inspect its current branch/content and integrate the files instead of force-pushing or overwriting anything.

## What to check after publishing

- `README.md` (English) and `README.zh-CN.md` (Chinese) are visible.
- `docs/meshlab-workflow.zh-CN.md` and `docs/feko-validation.zh-CN.md` display images properly.
- `SKILL.md` and `scripts/mesh_pipeline.py` are present.
- The repository does not contain `.cfx`, raw aircraft meshes, personal local paths or credentials.
- Run `python -m pytest -q tests` locally and note the result in the release.
