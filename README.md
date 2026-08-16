# XSMB Quant — Data Foundation

The project is rebuilt from the data plane upward.

## Authoritative data rule

The crawler collects and preserves the **full 27 prize values** in the official XSMB prize structure:

`DB/G1/G2/G3/G4/G5/G6/G7 = 1/1/2/6/4/6/3/4 = 27 values`.

`TAIL_27` is a derived view only: the last two digits of each full prize.

`Ket_Qua_Loto27.xlsx` is treated as a legacy tail-only reference dataset, not as forensic source truth.

## Pipeline

```text
source HTML
  -> raw HTML SHA256
  -> strict FULL_27 extraction
  -> source/day fingerprint
  -> cross-source quorum
  -> conflict ledger
  -> canonical FULL_27 XLSX
  -> derived TAIL_27
```

The runtime/UI is deliberately not part of this first foundation commit.