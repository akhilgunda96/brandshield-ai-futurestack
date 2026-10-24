# BrandShield AI

**TechCircuit · Grumpybot**

BrandShield helps a team check its content before it goes out. A creator submits a draft, the app checks it against the selected brand's guidelines, and a reviewer makes the final decision.

The idea is simple: if a product name is written incorrectly or a claim goes beyond an approved fact, the person writing the content should be able to see what needs attention and why.

## What you can do

- Review text against a brand's approved names, wording and facts.
- See the passage behind each finding, along with its severity and source.
- Apply a suggested correction, edit the draft yourself, or dismiss a finding with a reason.
- Leave comments and send a draft for approval.
- Approve a submission or request changes from a separate reviewer account.
- Look back at previous revisions and download a review report.
- Create brand profiles and check common finding categories on the dashboard.

The checks use configured Python rules. They cover specific wording and claim patterns, so a reviewer still needs to read the content in context.

## The two sample brands

| Brand | What its profile checks |
| --- | --- |
| EcoVolt | Product naming, promotional wording, energy-savings claims and their qualifications |
| NovaWear | Brand naming, sustainability wording, sales language and repeated exclamation marks |

Both brands and their guidelines are fictional. They give you something to try straight away. Managers can replace the sample guidance or add another brand through **Brand profiles**.

## Run the project

You will need Python 3.11 or newer. Extract the project and open a terminal inside the `brandshield` folder.

### Windows

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe demo.py
.venv\Scripts\python.exe -m streamlit run app.py
```

### macOS or Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python demo.py
.venv/bin/python -m streamlit run app.py
```

Open the address printed in the terminal, usually `http://localhost:8501`.

Running `demo.py` adds the sample accounts and a campaign for each brand. Use it only for a fresh installation. If you want to set up your own accounts instead, skip that command. The first visit will ask you to create an administrator password; you can then sign in as `admin` and add users.

### Sample accounts

| Username | Password | Role |
| --- | --- | --- |
| creator | BrandShield!2026 | Creates, edits and submits drafts |
| reviewer | BrandShield!2026 | Reviews submissions and records decisions |
| manager | BrandShield!2026 | Manages brand guidance and reviews submissions |
| admin | AdminDemo!2026 | Manages users and profiles, and can create or review content |

These passwords are for the local demo only. Use your own accounts for real content. Nobody can approve their own submission, including an administrator.

## Try a complete review

1. Sign in as `creator` and open **New review**.
2. Choose EcoVolt or NovaWear, enter a title, and click **Load fictional example**.
3. Click **Analyse & save draft**, then open the saved draft in **Reviews**.
4. Read the findings and their sources. Apply a correction or edit the content and save a new revision.
5. In **Comments & decisions**, add a note and request approval.
6. Sign out and sign in as `reviewer`. Open the submission, add a decision explanation, and approve it or request changes.

For EcoVolt, try changing the sample claim to:

> EcoVolt offers up to 15% energy savings under specified laboratory conditions.

Percentage findings need a manual edit to the full claim so its conditions are kept. Applying other suggestions also creates a new revision and runs the checks again.

A draft can be submitted with open findings; those findings remain visible to the reviewer. Approved content is locked. If changes are requested, the creator can revise and submit it again. Nothing is published automatically.

## Updating brand guidance

Creators and reviewers can read brand profiles. Managers and administrators can edit them or create new ones using the forms and tables on the profile page.

Each approved source has an ID, a title and its guidance text. Rules refer to those IDs so a finding can show where its explanation comes from. If you change a source ID, update the rules that use it before saving.

Existing reviews keep the guidance they started with. Start a new review when you want to check content against an updated profile.

## Files and tools

The app uses **Streamlit** for the interface, **Python** for the checks, **SQLite** for saved data, and **pypdf** for extracting PDF text.

| File | Purpose |
| --- | --- |
| `app.py` | Sign-in, dashboard and review screens |
| `engine.py` | Brand validation, content checks and suggested corrections |
| `store.py` | Database access, permissions and review states |
| `profiles_ui.py` | Brand profile display and editing forms |
| `brands.py` | NovaWear guidance and brand-specific examples |
| `theme.py` | Styling and dashboard components |
| `demo.py` | Sample accounts and reviews |
| `tests/` | Automated checks for the rules, storage and screens |

## Tests

After installing the requirements, run this from the project folder:

```bash
python -m unittest discover -s tests -v
```

The project includes 39 tests covering rule findings, text positions, source references, access permissions, revisions, approvals, brand separation and the main screens. Tests use temporary databases rather than your saved reviews.

## Saved data

Accounts, profiles and reviews are saved in `data/brandshield.sqlite3`. Keep a backup of that file if you need the review history. You can choose another location with the `BRANDSHIELD_DB` environment variable.

When updating the app, stop it, replace the application files, and restart it. **Keep your existing `data` folder.** There is no need to run `demo.py` again.

For hosting, use a Python environment with persistent storage. A temporary filesystem can lose the SQLite database when the host restarts.

## Current limits

This version focuses on text review. It accepts typed text, UTF-8 text and Markdown files, and PDFs with extractable text. Uploads are limited to 5 MB, PDFs to 50 pages, and content to 50,000 characters.

It does not read scanned images, check logos or verify every possible claim. Energy checks recognise particular percentage and qualification patterns; they can miss paraphrases or flag wording that needs a closer look. Missing evidence is shown as unverified, rather than treated as proof that a claim is false.

This is a hackathon prototype. Real-world accuracy, usability and time savings have not been measured yet.

## Team

- Akhil Gunda — Team lead and backend
- Dulam Nithin — UI and data
- Divyamsh Nagamalla — Rules and testing

## Hosted demo

Use `python launch.py` to start on a Python web host. Set `BRANDSHIELD_DEMO_MODE=true` to create fictional demo accounts on a fresh database. Existing databases are preserved. Render configuration is included in `render.yaml`; see `DEPLOYMENT.md` for the release checklist.
