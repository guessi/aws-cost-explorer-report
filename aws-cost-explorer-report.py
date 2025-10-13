#!/usr/bin/env python3

import boto3
import click
import csv
import sys
import time

from typing import Dict, List, Tuple, Generator, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
from calendar import monthrange
from datetime import datetime
from prettytable import PrettyTable

# define headers
HEADERS: List[str] = ['TimePeriodStart', 'LinkedAccount', 'Service', 'Amount']

# define constants
MIN_AMOUNT_THRESHOLD: float = 0.00001


def get_cost_data_generator(bclient: Any, start: str, end: str, threshold: float) -> Generator[Tuple[str, str, str, float], None, None]:
    """Generator that yields cost data items."""
    params: Dict[str, Any] = {
        'TimePeriod': {'Start': start, 'End': end},
        'Granularity': 'MONTHLY',
        'Metrics': ['UnblendedCost'],
        'GroupBy': [
            {'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'},
            {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        ]
    }

    page_count: int = 0
    max_pages: int = 50
    processed_items: int = 0

    while page_count < max_pages:
        retry_count: int = 0
        max_retries: int = 3

        while retry_count <= max_retries:
            try:
                data = bclient.get_cost_and_usage(**params)
                break
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ThrottlingException' and retry_count < max_retries:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** retry_count
                    click.echo(
                        f"API throttled, retrying in {wait_time}s...", err=True)
                    time.sleep(wait_time)
                    retry_count += 1
                else:
                    if error_code == 'ThrottlingException':
                        click.echo(
                            "Warning: API throttled, stopping pagination", err=True)
                        return
                    else:
                        click.echo(
                            f"Error: AWS API call failed - {e.response['Error']['Message']}", err=True)
                        sys.exit(1)
            except Exception as e:
                click.echo(f"Error: Unexpected error - {str(e)}", err=True)
                sys.exit(1)

        for result_by_time in data['ResultsByTime']:
            for group in result_by_time['Groups']:
                amount: float = float(
                    group['Metrics']['UnblendedCost']['Amount'])
                processed_items += 1

                if amount >= threshold:
                    yield (
                        result_by_time['TimePeriod']['Start'],
                        group['Keys'][0],
                        group['Keys'][1],
                        amount
                    )

        page_count += 1
        if processed_items % 1000 == 0 and processed_items > 0:
            click.echo(f"Processed {processed_items} items...", err=True)

        next_token: Optional[str] = data.get('NextPageToken')
        if not next_token:
            break
        params['NextPageToken'] = next_token

    if page_count >= max_pages:
        click.echo(
            f"Warning: Reached pagination limit ({max_pages} pages), results may be incomplete", err=True)


def process_cost_data_stream(bclient: Any, start: str, end: str, output_format: str, sort: bool, threshold: float, limit: int) -> None:
    """Process cost data using lazy evaluation and streaming."""
    cost_generator = get_cost_data_generator(bclient, start, end, threshold)

    if sort:
        # Use heap for memory-efficient top-K sorting
        import heapq
        top_items: List[Tuple[float, Tuple[str, str, str, float]]] = []
        total = 0

        for item in cost_generator:
            total += item[3]  # Add amount to total
            if len(top_items) < limit:
                heapq.heappush(top_items, (item[3], item))
            elif item[3] > top_items[0][0]:
                heapq.heapreplace(top_items, (item[3], item))

        # Convert heap to sorted list (largest first)
        rows = [item[1]
                for item in sorted(top_items, key=lambda x: x[0], reverse=True)]
        if len(top_items) >= limit:
            click.echo(
                f"Warning: Results limited to top {limit} items", err=True)
    else:
        # Stream processing without sorting
        rows = []
        total = 0

        for item in cost_generator:
            rows.append(item)
            total += item[3]  # Add amount to total

    format_and_output(rows, total, output_format, False)


def format_and_output(rows: List[Tuple[str, str, str, float]], total: float, output_format: str, sort: bool) -> None:
    """Format and output results with type safety."""
    if sort:
        rows.sort(key=lambda x: x[3], reverse=True)

    if output_format == 'csv':
        writer = csv.writer(sys.stdout)
        writer.writerow(HEADERS)
        for row in rows:
            display_row = [row[0], row[1], row[2], format(row[3], '0.5f')]
            writer.writerow(display_row)
        print(f"Total: {total:.5f}", file=sys.stderr)
    elif output_format == 'tsv':
        writer = csv.writer(sys.stdout, delimiter='\t')
        writer.writerow(HEADERS)
        for row in rows:
            display_row = [row[0], row[1], row[2], format(row[3], '0.5f')]
            writer.writerow(display_row)
        print(f"Total: {total:.5f}", file=sys.stderr)
    else:  # table format
        pt = PrettyTable()
        pt.field_names = HEADERS
        pt.align = "l"
        pt.align["LinkedAccount"] = "r"
        pt.align["Amount"] = "r"
        pt.max_width["Service"] = 50
        pt.border = True
        pt.header = True

        for row in rows:
            display_row = [row[0], row[1], row[2], format(row[3], '0.5f')]
            pt.add_row(display_row)
        print(pt)
        print(f"Total: {total:.5f}")


def process_results(results: list, output_format: str, sort: bool) -> None:
    rows = []
    total = 0

    for result_by_time in results:
        for group in result_by_time['Groups']:
            amount = float(group['Metrics']['UnblendedCost']['Amount'])
            total += amount

            # Skip, if total amount less than threshold USD
            if amount < MIN_AMOUNT_THRESHOLD:
                continue

            rows.append([
                result_by_time['TimePeriod']['Start'],
                group['Keys'][0],
                group['Keys'][1],
                amount,  # Store raw numeric value for sorting
            ])

    if sort:
        rows.sort(key=lambda x: x[3], reverse=True)

    if output_format == 'csv':
        # Format amounts for display
        display_rows = []
        for row in rows:
            display_row = row.copy()
            display_row[3] = format(row[3], '0.5f')
            display_rows.append(display_row)

        writer = csv.writer(sys.stdout)
        writer.writerow(HEADERS)
        writer.writerows(display_rows)
        print(f"Total: {total:.5f}")
    elif output_format == 'tsv':
        # Format amounts for display
        display_rows = []
        for row in rows:
            display_row = row.copy()
            display_row[3] = format(row[3], '0.5f')
            display_rows.append(display_row)

        writer = csv.writer(sys.stdout, delimiter='\t')
        writer.writerow(HEADERS)
        writer.writerows(display_rows)
        print(f"Total: {total:.5f}")
    else:  # table format
        pt = PrettyTable()
        pt.field_names = HEADERS
        pt.align = "l"
        pt.align["LinkedAccount"] = "r"
        pt.align["Amount"] = "r"
        pt.max_width["Service"] = 50
        pt.border = True
        pt.header = True

        for row in rows:
            display_row = row.copy()
            display_row[3] = format(row[3], '0.5f')
            pt.add_row(display_row)
        print(pt)
        print(f"Total: {total:.5f}")


@click.command()
@click.option('-P', '--profile', help='profile name')
@click.option('-S', '--start', help='start date (default: 1st date of current month)')
@click.option('-E', '--end', help='end date (default: last date of current month)')
@click.option('--sort/--no-sort', default=True)
@click.option('-o', '--output', type=click.Choice(['table', 'csv', 'tsv']), default='table', help='output format')
@click.option('--threshold', type=float, default=0.00001, help='minimum amount threshold (default: 0.00001)')
@click.option('--limit', type=int, default=1000, help='maximum number of results when sorting (default: 1000)')
def report(profile: Optional[str], start: Optional[str], end: Optional[str], sort: bool, output: str, threshold: float, limit: int) -> None:
    # validate user-provided dates first
    if start:
        try:
            start_date = datetime.strptime(start, '%Y-%m-%d')
            start = start_date.strftime('%Y-%m-%d')  # Normalize format

            if start_date > datetime.now():
                click.echo(
                    "Error: Start date cannot be in the future", err=True)
                sys.exit(1)
        except ValueError:
            click.echo(
                "Error: Start date must be in YYYY-MM-DD format (e.g., 2024-01-15)", err=True)
            sys.exit(1)

    if end:
        try:
            end_date = datetime.strptime(end, '%Y-%m-%d')
            end = end_date.strftime('%Y-%m-%d')  # Normalize format
        except ValueError:
            click.echo(
                "Error: End date must be in YYYY-MM-DD format (e.g., 2024-01-15)", err=True)
            sys.exit(1)

    # set start/end to current month if not specify
    if not start or not end:
        # get last day of month by `monthrange()`
        # ref: https://stackoverflow.com/a/43663
        ldom = monthrange(datetime.today().year, datetime.today().month)[1]

        if not start:
            start = datetime.today().replace(day=1).strftime('%Y-%m-%d')
        if not end:
            end = datetime.today().replace(day=ldom).strftime('%Y-%m-%d')

    # validate date order
    start_date = datetime.strptime(start, '%Y-%m-%d')
    end_date = datetime.strptime(end, '%Y-%m-%d')

    # validate date range size (AWS has 12-month limit for detailed data)
    date_diff = (end_date - start_date).days
    if date_diff <= 0:
        click.echo("Error: Start date must be before end date",
                   err=True)
        sys.exit(1)
    if date_diff > 365:
        click.echo("Error: Date range cannot exceed 365 days",
                   err=True)
        sys.exit(1)

    # cost explorer
    try:
        bclient = boto3.Session(profile_name=profile).client('ce')
        process_cost_data_stream(
            bclient, start, end, output, sort, threshold, limit)
    except NoCredentialsError:
        click.echo(
            "Error: AWS credentials not found. Configure your credentials or profile.",
            err=True)
        sys.exit(1)
    except ProfileNotFound:
        click.echo(
            f"Error: AWS profile '{profile}' not found. Check your profile name.",
            err=True)
        sys.exit(1)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ValidationException':
            click.echo(
                "Error: Invalid parameters for AWS Cost Explorer API.",
                err=True)
        elif error_code == 'AccessDeniedException':
            click.echo(
                "Error: Access denied. Check your AWS permissions for Cost Explorer.",
                err=True)
        else:
            click.echo(
                f"Error: AWS API call failed - {e.response['Error']['Message']}",
                err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: Unexpected error - {str(e)}",
                   err=True)
        sys.exit(1)


if __name__ == '__main__':
    report()
