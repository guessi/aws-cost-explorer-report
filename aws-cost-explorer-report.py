#!/usr/bin/env python3

import boto3
import click
import csv
import sys

from calendar import monthrange
from datetime import datetime
from prettytable import PrettyTable

# define headers
HEADERS = ['TimePeriodStart', 'LinkedAccount', 'Service', 'Amount']

# define table layout
pt = PrettyTable()
pt.field_names = HEADERS
pt.align = "l"
pt.align["Amount"] = "r"


def get_cost_and_usage(bclient: object, start: str, end: str) -> list:
    cu = []
    params = {
        'TimePeriod': {'Start': start, 'End': end},
        'Granularity': 'MONTHLY',
        'Metrics': ['UnblendedCost'],
        'GroupBy': [
            {'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'},
            {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        ]
    }

    while True:
        data = bclient.get_cost_and_usage(**params)
        cu.extend(data['ResultsByTime'])
        if not data.get('NextPageToken'):
            break

    return cu


def process_results(results: list, output_format: str, sort: bool) -> None:
    rows = []
    total = 0

    for result_by_time in results:
        for group in result_by_time['Groups']:
            amount = float(group['Metrics']['UnblendedCost']['Amount'])
            total += amount

            # Skip, if total amount less then 0.00001 USD
            if amount < 0.00001:
                continue

            rows.append([
                result_by_time['TimePeriod']['Start'],
                group['Keys'][0],
                group['Keys'][1],
                format(amount, '0.5f'),
            ])

    if sort:
        rows.sort(key=lambda x: float(x[3]), reverse=True)

    if output_format == 'csv':
        writer = csv.writer(sys.stdout)
        writer.writerow(HEADERS)
        writer.writerows(rows)
        print(f"Total: {total:.5f}")
    elif output_format == 'tsv':
        writer = csv.writer(sys.stdout, delimiter='\t')
        writer.writerow(HEADERS)
        writer.writerows(rows)
        print(f"Total: {total:.5f}")
    else:  # table format
        for row in rows:
            pt.add_row(row)
        print(pt.get_string(sortby="Amount", reversesort=True) if sort else pt)
        print(f"Total: {total:.5f}")


@click.command()
@click.option('-P', '--profile', help='profile name')
@click.option('-S', '--start', help='start date (default: 1st date of current month)')
@click.option('-E', '--end', help='end date (default: last date of current month)')
@click.option('--sort/--no-sort', default=False)
@click.option('-o', '--output', type=click.Choice(['table', 'csv', 'tsv']), default='table', help='output format')
def report(profile: str, start: str, end: str, sort: bool, output: str) -> None:
    # set start/end to current month if not specify
    if not start or not end:
        # get last day of month by `monthrange()`
        # ref: https://stackoverflow.com/a/43663
        ldom = monthrange(datetime.today().year, datetime.today().month)[1]

        start = datetime.today().replace(day=1).strftime('%Y-%m-%d')
        end = datetime.today().replace(day=ldom).strftime('%Y-%m-%d')

    # cost explorer
    SERVICE_NAME = 'ce'
    bclient = boto3.Session(profile_name=profile).client(SERVICE_NAME)

    results = get_cost_and_usage(bclient, start, end)
    process_results(results, output, sort)


if __name__ == '__main__':
    report()
