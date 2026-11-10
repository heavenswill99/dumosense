# Health Reserve point-in-time training inputs

These files are bundled so the feature engineering and model run can be reproduced without downloading models.

- `health_reserve_assessments.csv` is the existing synthetic Health Reserve assessment table from this repository.
- The other eight CSV files are from `data-engineering-foundations` at commit `5d33e493a5d612497483a6ceed42643a8c46d53e`.
- All records are synthetic. Plan rows are simulation-only; outcome rows are synthetic follow-ups.
- The later scenario table and the synthetic healthcare cost-reference table are not in this training input bundle. Scenarios post-date every plan choice; reference costs are assumptions and do not provide an observed outcome.
- The training script records SHA-256 hashes for each CSV in the run's `metrics.json` and `manifest.json`.

Do not treat these as real household financial records or use resulting weights to recommend real contribution amounts.
