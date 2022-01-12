# AWS Cost Explorer Pretty Report written in Python

## Prerequisites

- Python 3.7 (or later)


## Setup Requirements

```bash
$ pipenv install
```

or

```bash
$ pip3 install -r requirements.txt
```

## Usage

```bash
$ ./aws-cost-explorer-report.py --help

Usage: aws-cost-explorer-report.py [OPTIONS]

Options:
  -P, --profile TEXT  profile name
  -S, --start TEXT    start date (default: 1st date of current month)
  -E, --end TEXT      end date (default: last date of current month)
  --help              Show this message and exit.
```

## Examples

check cost explorer report of date range [2022-01-01,2022-01-31]

```bash
$ ./aws-cost-explorer-report.py -P my-profile -S 2022-01-01 -E 2022-01-31

+-----------------+---------------+----------------------------------------+------------+
| TimePeriodStart | LinkedAccount | Service                                |     Amount |
+-----------------+---------------+----------------------------------------+------------+
| 2022-01-01      | 123456789012  | AWS Key Management Service             |    1.39938 |
| 2022-01-01      | 123456789012  | AWS Lambda                             |    3.00102 |
| 2022-01-01      | 123456789012  | EC2 - Other                            |   11.48211 |
| 2022-01-01      | 123456789012  | Amazon Elastic Compute Cloud - Compute |  102.41709 |
| 2022-01-01      | 123456789012  | Amazon Elastic Load Balancing          |   17.73890 |
| 2022-01-01      | 123456789012  | Amazon Route 53                        |    1.32980 |
| 2022-01-01      | 123456789012  | Amazon Simple Notification Service     |    2.32891 |
| 2022-01-01      | 123456789012  | Amazon Simple Storage Service          |    3.34789 |
| 2022-01-01      | 123456789012  | AmazonCloudWatch                       |   10.32789 |
| 2022-01-01      | 123456789012  | AWS Key Management Service             |    3.97408 |
| 2022-01-01      | 123456789012  | AWS Lambda                             |   23.44120 |
| 2022-01-01      | 123456789012  | EC2 - Other                            |   12.30661 |
| 2022-01-01      | 123456789012  | Amazon Elastic Compute Cloud - Compute |  127.45739 |
| 2022-01-01      | 123456789012  | Amazon Elastic Load Balancing          |   18.15638 |
| 2022-01-01      | 123456789012  | Amazon Route 53                        |    1.32456 |
| 2022-01-01      | 123456789012  | Amazon Simple Notification Service     |    2.00011 |
| 2022-01-01      | 123456789012  | Amazon Simple Storage Service          |    3.63218 |
| 2022-01-01      | 123456789012  | AmazonCloudWatch                       |   10.06860 |
+-----------------+---------------+----------------------------------------+------------+
```

## Equivalent command with `awscli`

check cost explorer report of date range [2022-01-01,2022-01-31]

```bash
$ aws --profile my-profile \
    ce get-cost-and-usage \
      --time-period "Start=2022-01-01,End=2022-01-31" \
      --granularity "MONTHLY" \
      --metrics "UnblendedCost" \
      --group-by "Type=DIMENSION,Key=LINKED_ACCOUNT" \
      --group-by "Type=DIMENSION,Key=SERVICE" \
      --output json
```

# License

[MIT LICENSE](LICENSE)
