# AWS Cost Explorer Pretty Report written in Python

## Prerequisites

- Python 3.10 (or later)


## Setup Requirements

```bash
$ pipenv install
```

## Usage

```bash
$ ./aws-cost-explorer-report.py --help

Usage: aws-cost-explorer-report.py [OPTIONS]

Options:
  -P, --profile TEXT            profile name
  -S, --start TEXT              start date (default: 1st date of current
                                month)
  -E, --end TEXT                end date (default: last date of current month)
  --sort / --no-sort
  -o, --output [table|csv|tsv]  output format
  --help                        Show this message and exit.
```

## Examples

check cost explorer report of date range [2024-01-01,2024-01-31]

```bash
$ ./aws-cost-explorer-report.py -P my-profile -S 2024-01-01 -E 2024-01-31

+-----------------+---------------+----------------------------------------+------------+
| TimePeriodStart | LinkedAccount | Service                                |     Amount |
+-----------------+---------------+----------------------------------------+------------+
| 2024-01-01      | 123456789012  | AWS Key Management Service             |    1.39938 |
| 2024-01-01      | 123456789012  | AWS Lambda                             |    3.00102 |
| ...             | ...           | ...                                    |        ... |
+-----------------+---------------+----------------------------------------+------------+
Total: 103.65606
```

## Equivalent command with `awscli`

check cost explorer report of date range [2024-01-01,2024-01-31]

```bash
$ aws --profile my-profile \
    ce get-cost-and-usage \
      --time-period "Start=2024-01-01,End=2024-01-31" \
      --granularity "MONTHLY" \
      --metrics "UnblendedCost" \
      --group-by "Type=DIMENSION,Key=LINKED_ACCOUNT" \
      --group-by "Type=DIMENSION,Key=SERVICE" \
      --output json
```

# License

[MIT LICENSE](LICENSE)
