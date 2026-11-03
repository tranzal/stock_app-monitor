# STOCKLY external monitor

This public repository contains only an independent availability checker. The application repository stays private. No application source, API keys, account details, personal access logs, or market data are included.

The standard GitHub-hosted Linux workflow runs approximately every 15 minutes and can also run from **Actions → STOCKLY external availability → Run workflow**. It checks the public website (200) and unauthenticated `/v1/auth/me` response (401). It does not log in or invoke collection, forecasts, paid APIs, or GPT. There are no repository secrets to configure; the temporary built-in GitHub token can only read this repository and manage its issues.

Three unsuccessful checks separated by 20 seconds open one incident assigned to the owner. Further failures reuse it. Two successful recovery checks close it with one recovery comment. Enable repository **Watch → All activity** and GitHub email notifications to receive both events. Workflow failures also appear in Actions. The monitor cannot distinguish a power failure, internet outage, DNS issue, or application failure.

Standard GitHub-hosted runners for public repositories do not consume a private repository's included minutes. Scheduling is best effort, may be delayed, and GitHub can disable scheduled workflows after 60 days without repository activity. Check the last run shown in the application's administrator operations screen; use **Enable workflow** or a manual run if needed. This is not a guaranteed uptime service.

To publish from the private application repository, copy exactly `monitor.py`, `README.md`, and `monitor.yml` to `.github/workflows/monitor.yml`. Never copy the application tree or local configuration.
