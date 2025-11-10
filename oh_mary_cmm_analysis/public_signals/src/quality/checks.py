#!/usr/bin/env python3
"""
Data Quality Checks & Anomaly Detection

Provides:
- Coverage reports by source
- Anomaly detection (sudden spikes/drops)
- Timestamp monotonicity checks
- Schema validation
- Data completeness metrics
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CoverageMetrics:
    """Coverage metrics for a data source."""
    source: str
    total_observations: int
    non_null_observations: int
    coverage_pct: float
    shows_covered: int
    weeks_covered: int


@dataclass
class AnomalyDetection:
    """Anomaly detection result."""
    show: str
    week_start: str
    metric: str
    value: float
    median_prior_8w: float
    ratio_to_median: float
    is_anomaly: bool
    anomaly_type: str  # 'spike' or 'drop'


@dataclass
class ValidationReport:
    """Complete validation report."""
    timestamp: str
    total_rows: int
    total_columns: int
    coverage: List[CoverageMetrics]
    anomalies: List[AnomalyDetection]
    schema_valid: bool
    schema_errors: List[str]
    timestamp_issues: List[str]
    status: str  # 'OK' or 'ACTION_NEEDED'


def calculate_coverage(
    df: pd.DataFrame,
    source_metrics: Dict[str, List[str]]
) -> List[CoverageMetrics]:
    """
    Calculate coverage metrics by source.

    Args:
        df: Weekly panel DataFrame
        source_metrics: Dict mapping source name to list of metric columns
                       e.g., {'tiktok': ['tt_posts', 'tt_sum_views'], ...}

    Returns:
        List of CoverageMetrics objects

    Example:
        >>> metrics = {'tiktok': ['tt_posts', 'tt_sum_views']}
        >>> coverage = calculate_coverage(df, metrics)
    """
    coverage_list = []

    for source, metrics in source_metrics.items():
        # Filter to existing columns
        existing_metrics = [m for m in metrics if m in df.columns]

        if not existing_metrics:
            logger.warning(f"No metrics found for {source}")
            continue

        # Calculate coverage for first metric as representative
        metric = existing_metrics[0]

        non_null = df[metric].notna().sum()
        total = len(df)
        coverage_pct = (non_null / total * 100) if total > 0 else 0.0

        # Count unique shows and weeks with data
        with_data = df[df[metric].notna()]
        shows_covered = with_data['show'].nunique() if 'show' in df.columns else 0
        weeks_covered = with_data['week_start'].nunique() if 'week_start' in df.columns else 0

        coverage_list.append(CoverageMetrics(
            source=source,
            total_observations=total,
            non_null_observations=non_null,
            coverage_pct=coverage_pct,
            shows_covered=shows_covered,
            weeks_covered=weeks_covered
        ))

        logger.info(f"{source:20s}: {coverage_pct:5.1f}% coverage ({non_null}/{total} obs)")

    return coverage_list


def detect_anomalies(
    df: pd.DataFrame,
    metrics: List[str],
    threshold: float = 5.0,
    lookback_weeks: int = 8
) -> List[AnomalyDetection]:
    """
    Detect anomalies using simple spike/drop detection.

    Flags weeks where a metric jumps >threshold× median of prior lookback_weeks.

    Args:
        df: Weekly panel DataFrame (must be sorted by show, week_start)
        metrics: Metrics to check for anomalies
        threshold: Multiplier for anomaly detection (default: 5.0)
        lookback_weeks: Number of prior weeks to use for baseline (default: 8)

    Returns:
        List of AnomalyDetection objects

    Example:
        >>> anomalies = detect_anomalies(df, ['tt_sum_views', 'ig_sum_likes'])
    """
    if 'show' not in df.columns or 'week_start' not in df.columns:
        logger.warning("DataFrame missing 'show' or 'week_start', skipping anomaly detection")
        return []

    # Sort
    df = df.sort_values(['show', 'week_start']).reset_index(drop=True)

    anomalies = []

    for metric in metrics:
        if metric not in df.columns:
            continue

        # Calculate rolling median of prior weeks (shift by 1 to exclude current week)
        df[f'_{metric}_median_prior'] = df.groupby('show')[metric].transform(
            lambda x: x.shift(1).rolling(lookback_weeks, min_periods=1).median()
        )

        # Calculate ratio
        df[f'_{metric}_ratio'] = df[metric] / df[f'_{metric}_median_prior']

        # Detect spikes (>threshold)
        spikes = df[df[f'_{metric}_ratio'] > threshold].copy()

        for _, row in spikes.iterrows():
            anomalies.append(AnomalyDetection(
                show=str(row['show']),
                week_start=str(row['week_start']),
                metric=metric,
                value=float(row[metric]),
                median_prior_8w=float(row[f'_{metric}_median_prior']),
                ratio_to_median=float(row[f'_{metric}_ratio']),
                is_anomaly=True,
                anomaly_type='spike'
            ))

        # Detect drops (<1/threshold)
        drops = df[(df[f'_{metric}_ratio'] < 1/threshold) & (df[f'_{metric}_ratio'] > 0)].copy()

        for _, row in drops.iterrows():
            anomalies.append(AnomalyDetection(
                show=str(row['show']),
                week_start=str(row['week_start']),
                metric=metric,
                value=float(row[metric]),
                median_prior_8w=float(row[f'_{metric}_median_prior']),
                ratio_to_median=float(row[f'_{metric}_ratio']),
                is_anomaly=True,
                anomaly_type='drop'
            ))

        # Cleanup temp columns
        df.drop(columns=[f'_{metric}_median_prior', f'_{metric}_ratio'], inplace=True)

    if anomalies:
        logger.warning(f"Detected {len(anomalies)} anomalies")
    else:
        logger.info("No anomalies detected")

    return anomalies


def check_timestamp_monotonicity(df: pd.DataFrame) -> List[str]:
    """
    Check that timestamps are monotonically increasing within each show.

    Args:
        df: Panel DataFrame

    Returns:
        List of error messages

    Example:
        >>> errors = check_timestamp_monotonicity(df)
    """
    if 'show' not in df.columns or 'week_start' not in df.columns:
        return ["Missing 'show' or 'week_start' column"]

    errors = []

    # Convert to datetime
    df = df.copy()
    df['week_start_dt'] = pd.to_datetime(df['week_start'])

    # Check for duplicates within show
    for show in df['show'].unique():
        show_df = df[df['show'] == show].sort_values('week_start_dt')

        # Check for duplicate week_starts
        duplicates = show_df['week_start'].duplicated().sum()
        if duplicates > 0:
            errors.append(f"Show '{show}': {duplicates} duplicate week_starts")

        # Check for non-monotonic timestamps
        diffs = show_df['week_start_dt'].diff()
        non_monotonic = (diffs < pd.Timedelta(0)).sum()

        if non_monotonic > 0:
            errors.append(f"Show '{show}': {non_monotonic} non-monotonic timestamps")

    if errors:
        logger.warning(f"Timestamp issues: {len(errors)} problems found")
    else:
        logger.info("✓ Timestamps are monotonic")

    return errors


def validate_week_binning(df: pd.DataFrame) -> List[str]:
    """
    Validate that week_start values are correct (Mondays).

    Args:
        df: Panel DataFrame

    Returns:
        List of error messages

    Example:
        >>> errors = validate_week_binning(df)
    """
    if 'week_start' not in df.columns:
        return ["Missing 'week_start' column"]

    errors = []

    df = df.copy()
    df['week_start_dt'] = pd.to_datetime(df['week_start'])

    # Check that all week_start values are Mondays
    not_monday = df[df['week_start_dt'].dt.dayofweek != 0]

    if not not_monday.empty:
        errors.append(f"{len(not_monday)} week_start values are not Mondays")

    if errors:
        logger.warning(f"Week binning issues: {len(errors)} problems found")
    else:
        logger.info("✓ Week binning is correct (all Mondays)")

    return errors


def calculate_completeness(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate completeness (% non-null) for each column.

    Args:
        df: DataFrame

    Returns:
        Dict mapping column name to completeness percentage

    Example:
        >>> completeness = calculate_completeness(df)
        >>> print(completeness['tt_sum_views'])
        85.5
    """
    completeness = {}

    for col in df.columns:
        non_null = df[col].notna().sum()
        total = len(df)
        pct = (non_null / total * 100) if total > 0 else 0.0
        completeness[col] = pct

    return completeness


def generate_validation_report(
    df: pd.DataFrame,
    source_metrics: Optional[Dict[str, List[str]]] = None,
    anomaly_metrics: Optional[List[str]] = None,
    anomaly_threshold: float = 5.0,
    schema_validator: Optional[callable] = None
) -> ValidationReport:
    """
    Generate comprehensive validation report.

    Args:
        df: Weekly panel DataFrame
        source_metrics: Dict mapping sources to metric columns
        anomaly_metrics: Metrics to check for anomalies
        anomaly_threshold: Threshold for anomaly detection
        schema_validator: Function to validate schema (returns bool, List[str])

    Returns:
        ValidationReport object

    Example:
        >>> report = generate_validation_report(
        ...     df,
        ...     source_metrics={'tiktok': ['tt_posts', 'tt_sum_views']},
        ...     anomaly_metrics=['tt_sum_views', 'ig_sum_likes']
        ... )
        >>> print(report.status)
        'OK' or 'ACTION_NEEDED'
    """
    from datetime import datetime

    logger.info("\n" + "="*70)
    logger.info("VALIDATION REPORT")
    logger.info("="*70 + "\n")

    # Default source metrics
    if source_metrics is None:
        source_metrics = {
            'tiktok': ['tt_posts', 'tt_sum_views', 'tt_sum_likes'],
            'instagram': ['ig_posts', 'ig_sum_likes'],
            'google_trends': ['gt_index']
        }

    # Default anomaly metrics
    if anomaly_metrics is None:
        anomaly_metrics = [
            'tt_sum_views', 'tt_sum_likes', 'tt_posts',
            'ig_sum_likes', 'ig_posts', 'gt_index'
        ]

    # Coverage
    logger.info("COVERAGE:")
    coverage = calculate_coverage(df, source_metrics)

    # Anomalies
    logger.info("\nANOMALIES:")
    anomalies = detect_anomalies(df, anomaly_metrics, threshold=anomaly_threshold)

    # Schema validation
    schema_valid = True
    schema_errors = []

    if schema_validator:
        logger.info("\nSCHEMA:")
        schema_valid, schema_errors = schema_validator(df)
        if schema_valid:
            logger.info("✓ Schema is valid")
        else:
            logger.error(f"✗ Schema validation failed: {len(schema_errors)} errors")

    # Timestamp checks
    logger.info("\nTIMESTAMPS:")
    timestamp_issues = check_timestamp_monotonicity(df)
    timestamp_issues.extend(validate_week_binning(df))

    # Determine status
    min_coverage = min([c.coverage_pct for c in coverage]) if coverage else 0.0
    has_critical_anomalies = len(anomalies) > 10
    has_schema_errors = not schema_valid
    has_timestamp_issues = len(timestamp_issues) > 0

    if has_schema_errors or has_timestamp_issues:
        status = "ACTION_NEEDED"
    elif min_coverage < 60.0:
        status = "ACTION_NEEDED"
        logger.warning(f"Coverage below 60% threshold: {min_coverage:.1f}%")
    elif has_critical_anomalies:
        status = "ACTION_NEEDED"
        logger.warning(f"High anomaly count: {len(anomalies)}")
    else:
        status = "OK"

    # Create report
    report = ValidationReport(
        timestamp=datetime.now().isoformat(),
        total_rows=len(df),
        total_columns=len(df.columns),
        coverage=coverage,
        anomalies=anomalies[:100],  # Limit to first 100
        schema_valid=schema_valid,
        schema_errors=schema_errors,
        timestamp_issues=timestamp_issues,
        status=status
    )

    logger.info("\n" + "="*70)
    logger.info(f"STATUS: {status}")
    logger.info("="*70 + "\n")

    return report


def print_validation_summary(report: ValidationReport):
    """
    Print human-readable validation summary.

    Args:
        report: ValidationReport object

    Example:
        >>> print_validation_summary(report)
    """
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    print(f"\nTimestamp: {report.timestamp}")
    print(f"Dataset: {report.total_rows} rows × {report.total_columns} columns")
    print(f"Status: {report.status}\n")

    print("COVERAGE BY SOURCE:")
    print("-" * 70)
    for cov in report.coverage:
        print(f"  {cov.source:20s}: {cov.coverage_pct:5.1f}% "
              f"({cov.non_null_observations}/{cov.total_observations} obs, "
              f"{cov.shows_covered} shows, {cov.weeks_covered} weeks)")

    if report.anomalies:
        print(f"\nANOMALIES: {len(report.anomalies)} detected")
        print("-" * 70)
        for anom in report.anomalies[:10]:  # Show first 10
            print(f"  {anom.anomaly_type.upper():6s} | {anom.show:20s} | "
                  f"{anom.week_start} | {anom.metric:20s} | "
                  f"{anom.value:.0f} (vs {anom.median_prior_8w:.0f}, "
                  f"{anom.ratio_to_median:.1f}×)")
        if len(report.anomalies) > 10:
            print(f"  ... and {len(report.anomalies) - 10} more")

    if not report.schema_valid:
        print(f"\nSCHEMA ERRORS: {len(report.schema_errors)}")
        print("-" * 70)
        for err in report.schema_errors:
            print(f"  ✗ {err}")

    if report.timestamp_issues:
        print(f"\nTIMESTAMP ISSUES: {len(report.timestamp_issues)}")
        print("-" * 70)
        for issue in report.timestamp_issues:
            print(f"  ✗ {issue}")

    print("\n" + "="*70)
    if report.status == "OK":
        print("✓ Data quality checks passed")
    else:
        print("⚠ ACTION NEEDED - please review issues above")
    print("="*70 + "\n")


def save_validation_report(report: ValidationReport, output_path: str):
    """
    Save validation report to JSON file.

    Args:
        report: ValidationReport object
        output_path: Path to save JSON file

    Example:
        >>> save_validation_report(report, "data/panel/validation_report.json")
    """
    from pathlib import Path

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict
    report_dict = asdict(report)

    # Save
    with open(output_file, 'w') as f:
        json.dump(report_dict, f, indent=2)

    logger.info(f"✓ Saved validation report: {output_file}")
