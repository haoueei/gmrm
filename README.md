# Anonymous Website

This repository includes the code and supplementary materials related to the paper submission.

- The contents are anonymized for the purpose of double-anonymous submissions.
- However, the code and results related to the paper are available on the website, and anyone can install and test it by following the provided instructions.

## Online hardware replay

The `Online Hardware Validation` section uses `_includes/realtime.html` and `assets/realtime/`. Four trial JSON files and their videos load on selection; raw experiment logs are not published. `_checks/` is excluded automatically by Jekyll.

Validate the assets with `python3 _checks/check_replay.py` and `node --check assets/realtime/replay.js`. Build using the existing Jekyll environment with `bundle exec jekyll build --baseurl /gmrm --destination /tmp/gmrm-site-preview/gmrm`. Keep generated output outside the tracked `_site/` directory. For a local server with video seeking, run `python3 _checks/preview.py /tmp/gmrm-site-preview`, then open `http://localhost:4002/gmrm/#online-hardware`.

The integration preserves the corrected video timestamp mapping (approximately 0.21–0.25 s correction relative to the original replay). The 50 Hz hardware trials are separate from the existing 40 Hz simulation examples.
