"""Cultural Movement Marketing (CMM) metrics calculator."""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class CMMMetricsCalculator:
    """Calculates CMM metrics from discourse data."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize metrics calculator.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.confidence_level = config.get('output', {}).get('confidence_level', 0.95)

    def calculate_all_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate all CMM metrics.

        Args:
            df: DataFrame with discourse features and labels

        Returns:
            Dictionary of all metrics
        """
        print("\n📊 Calculating CMM Metrics...")

        metrics = {}

        # 1. Movement Sentiment Score (MSS)
        metrics['MSS'] = self.calculate_movement_sentiment_score(df)

        # 2. Identity Resonance Index (IRI)
        metrics['IRI'] = self.calculate_identity_resonance_index(df)

        # 3. Evangelism Ratio (ER)
        metrics['ER'] = self.calculate_evangelism_ratio(df)

        # 4. Repeat Attendance Signal (RAS)
        metrics['RAS'] = self.calculate_repeat_attendance_signal(df)

        # 5. Belonging Intensity Score (BIS)
        metrics['BIS'] = self.calculate_belonging_intensity_score(df)

        # 6. Gatekeeping & Insider Markers (GIM)
        metrics['GIM'] = self.calculate_gatekeeping_markers(df)

        # 7. Community Formation Signals (CFS)
        metrics['CFS'] = self.calculate_community_formation_signals(df)

        # 8. Mimetic Propagation Index (MPI)
        metrics['MPI'] = self.calculate_mimetic_propagation_index(df)

        # Overall CMM Score
        metrics['Overall_CMM_Score'] = self.calculate_overall_cmm_score(metrics)

        return metrics

    def calculate_movement_sentiment_score(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate Movement Sentiment Score (MSS).

        Measures engagement lift when audience uses collective language vs individual.
        """
        # Separate posts with collective vs individual language
        collective_posts = df[df['collective_voice'] == True]
        individual_posts = df[df['collective_voice'] == False]

        if len(collective_posts) == 0 or len(individual_posts) == 0:
            return {
                'score': 0.0,
                'collective_avg_engagement': 0.0,
                'individual_avg_engagement': 0.0,
                'lift_percentage': 0.0,
                'statistical_significance': False,
                'interpretation': 'Insufficient data for comparison'
            }

        # Calculate average engagement (using score/likes as proxy)
        collective_eng = collective_posts.get('engagement_score', collective_posts.get('score', pd.Series([0]))).mean()
        individual_eng = individual_posts.get('engagement_score', individual_posts.get('score', pd.Series([0]))).mean()

        # Calculate lift
        if individual_eng > 0:
            lift = ((collective_eng - individual_eng) / individual_eng) * 100
        else:
            lift = 0.0

        # Statistical significance test (t-test)
        collective_vals = collective_posts.get('engagement_score', collective_posts.get('score', pd.Series([0]))).values
        individual_vals = individual_posts.get('engagement_score', individual_posts.get('score', pd.Series([0]))).values

        if SCIPY_AVAILABLE:
            try:
                t_stat, p_value = stats.ttest_ind(collective_vals, individual_vals)
                significant = p_value < 0.05
            except:
                p_value = 1.0
                significant = False
        else:
            # Fallback if scipy not available
            p_value = 1.0
            significant = False

        # Calculate confidence intervals
        collective_ci = self._bootstrap_ci(collective_vals)
        individual_ci = self._bootstrap_ci(individual_vals)

        interpretation = self._interpret_mss(lift, significant)

        return {
            'score': float(collective_eng / max(individual_eng, 1)),
            'collective_avg_engagement': float(collective_eng),
            'individual_avg_engagement': float(individual_eng),
            'lift_percentage': float(lift),
            'statistical_significance': significant,
            'p_value': float(p_value),
            'collective_ci': collective_ci,
            'individual_ci': individual_ci,
            'n_collective': len(collective_posts),
            'n_individual': len(individual_posts),
            'interpretation': interpretation
        }

    def calculate_identity_resonance_index(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate Identity Resonance Index (IRI).

        Frequency + engagement of "felt seen/represented" language.
        """
        identity_posts = df[df['identity_resonance'] == True]

        if len(identity_posts) == 0:
            return {
                'score': 0.0,
                'frequency': 0.0,
                'avg_engagement': 0.0,
                'interpretation': 'No identity resonance detected'
            }

        frequency = len(identity_posts) / len(df)
        avg_engagement = identity_posts.get('engagement_score', identity_posts.get('score', pd.Series([0]))).mean()

        # Combined score: frequency × engagement (normalized)
        score = frequency * (avg_engagement / df.get('engagement_score', df.get('score', pd.Series([1]))).mean())

        # Confidence interval
        engagement_vals = identity_posts.get('engagement_score', identity_posts.get('score', pd.Series([0]))).values
        ci = self._bootstrap_ci(engagement_vals)

        interpretation = self._interpret_iri(frequency, score)

        return {
            'score': float(score),
            'frequency': float(frequency),
            'percentage': float(frequency * 100),
            'avg_engagement': float(avg_engagement),
            'n_posts': len(identity_posts),
            'ci': ci,
            'interpretation': interpretation
        }

    def calculate_evangelism_ratio(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate Evangelism Ratio (ER).

        Percentage of posts urging others to attend.
        """
        evangelism_posts = df[df['evangelism'] == True]

        ratio = len(evangelism_posts) / len(df) if len(df) > 0 else 0.0

        # Bootstrap confidence interval for proportion
        ci = self._bootstrap_proportion_ci(len(evangelism_posts), len(df))

        interpretation = self._interpret_er(ratio)

        return {
            'score': float(ratio),
            'percentage': float(ratio * 100),
            'n_evangelism_posts': len(evangelism_posts),
            'total_posts': len(df),
            'ci': ci,
            'interpretation': interpretation
        }

    def calculate_repeat_attendance_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate Repeat Attendance Signal (RAS).

        Percentage of posts referencing 2+ viewings or future intent.
        """
        repeat_posts = df[df['repeat_attendance'] == True]

        ratio = len(repeat_posts) / len(df) if len(df) > 0 else 0.0

        # Bootstrap confidence interval
        ci = self._bootstrap_proportion_ci(len(repeat_posts), len(df))

        interpretation = self._interpret_ras(ratio)

        return {
            'score': float(ratio),
            'percentage': float(ratio * 100),
            'n_repeat_posts': len(repeat_posts),
            'total_posts': len(df),
            'ci': ci,
            'interpretation': interpretation
        }

    def calculate_belonging_intensity_score(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate Belonging Intensity Score (BIS).

        NLP measure of belonging/emotional significance words.
        """
        belonging_posts = df[df['belonging_signal'] == True]

        # Average belonging terms per post
        avg_belonging_terms = df['belonging_terms_count'].mean()

        # Intensity: weighted by emotion markers
        intensity = (
            df['belonging_terms_count'] +
            df['emotion_intensity_count'] * 0.5
        ).mean()

        frequency = len(belonging_posts) / len(df) if len(df) > 0 else 0.0

        # Combined score
        score = frequency * intensity

        interpretation = self._interpret_bis(frequency, intensity)

        return {
            'score': float(score),
            'frequency': float(frequency),
            'avg_belonging_terms': float(avg_belonging_terms),
            'intensity': float(intensity),
            'n_posts': len(belonging_posts),
            'interpretation': interpretation
        }

    def calculate_gatekeeping_markers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate Gatekeeping & Insider Markers (GIM).

        Count of "if you know you know", inside jokes, ritual talk.
        """
        gatekeeping_posts = df[df['insider_gatekeeping'] == True]

        frequency = len(gatekeeping_posts) / len(df) if len(df) > 0 else 0.0
        avg_markers = df['gatekeeping_terms_count'].mean()

        interpretation = self._interpret_gim(frequency)

        return {
            'score': float(frequency),
            'percentage': float(frequency * 100),
            'avg_markers_per_post': float(avg_markers),
            'n_posts': len(gatekeeping_posts),
            'interpretation': interpretation
        }

    def calculate_community_formation_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate Community Formation Signals (CFS).

        Evidence of rush line communities, meetups, shared rituals.
        """
        community_posts = df[df['community_reference'] == True]

        frequency = len(community_posts) / len(df) if len(df) > 0 else 0.0

        # Look for specific community types
        rush_line = df['original_text'].str.contains('rush line', case=False, na=False).sum()
        lottery = df['original_text'].str.contains('lottery', case=False, na=False).sum()
        meetup = df['original_text'].str.contains('meet', case=False, na=False).sum()

        interpretation = self._interpret_cfs(frequency, rush_line, lottery)

        return {
            'score': float(frequency),
            'percentage': float(frequency * 100),
            'n_community_posts': len(community_posts),
            'rush_line_mentions': int(rush_line),
            'lottery_mentions': int(lottery),
            'meetup_mentions': int(meetup),
            'interpretation': interpretation
        }

    def calculate_mimetic_propagation_index(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate Mimetic Propagation Index (MPI).

        Number and persistence of audience-generated memes/motifs.
        """
        # This requires motif data (calculated separately)
        # For now, use proxy: repeated phrases and patterns

        # Simple proxy: engagement variance (high variance = viral spread)
        engagement_vals = df.get('engagement_score', df.get('score', pd.Series([0]))).values

        if len(engagement_vals) > 0:
            variance = np.var(engagement_vals)
            mean = np.mean(engagement_vals)
            cv = variance / (mean + 1)  # Coefficient of variation
        else:
            cv = 0.0

        # Check for viral indicators (high engagement outliers)
        if len(engagement_vals) > 0:
            q95 = np.percentile(engagement_vals, 95)
            viral_posts = (engagement_vals > q95).sum()
        else:
            viral_posts = 0

        interpretation = self._interpret_mpi(viral_posts, len(df))

        return {
            'score': float(cv),
            'coefficient_of_variation': float(cv),
            'n_viral_posts': int(viral_posts),
            'total_posts': len(df),
            'interpretation': interpretation
        }

    def calculate_overall_cmm_score(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate overall CMM score from individual metrics.

        Args:
            metrics: Dictionary of all calculated metrics

        Returns:
            Overall CMM score and interpretation
        """
        # Weight different metrics
        weights = {
            'MSS': 0.15,
            'IRI': 0.20,
            'ER': 0.15,
            'RAS': 0.15,
            'BIS': 0.15,
            'GIM': 0.10,
            'CFS': 0.10
        }

        weighted_sum = 0.0
        for metric, weight in weights.items():
            if metric in metrics:
                weighted_sum += metrics[metric]['score'] * weight

        # Normalize to 0-100
        overall_score = min(weighted_sum * 100, 100)

        interpretation = self._interpret_overall_cmm(overall_score)

        return {
            'score': float(overall_score),
            'interpretation': interpretation,
            'category': self._categorize_cmm_level(overall_score)
        }

    def _bootstrap_ci(self, data: np.ndarray, n_iterations: int = 1000) -> Tuple[float, float]:
        """Calculate bootstrap confidence interval."""
        if len(data) == 0:
            return (0.0, 0.0)

        bootstrap_means = []
        for _ in range(n_iterations):
            sample = np.random.choice(data, size=len(data), replace=True)
            bootstrap_means.append(np.mean(sample))

        alpha = 1 - self.confidence_level
        lower = np.percentile(bootstrap_means, alpha/2 * 100)
        upper = np.percentile(bootstrap_means, (1 - alpha/2) * 100)

        return (float(lower), float(upper))

    def _bootstrap_proportion_ci(self, successes: int, total: int, n_iterations: int = 1000) -> Tuple[float, float]:
        """Calculate bootstrap CI for proportion."""
        if total == 0:
            return (0.0, 0.0)

        proportions = []
        for _ in range(n_iterations):
            sample = np.random.binomial(total, successes/total)
            proportions.append(sample / total)

        alpha = 1 - self.confidence_level
        lower = np.percentile(proportions, alpha/2 * 100)
        upper = np.percentile(proportions, (1 - alpha/2) * 100)

        return (float(lower), float(upper))

    # Interpretation methods
    def _interpret_mss(self, lift: float, significant: bool) -> str:
        """Interpret Movement Sentiment Score."""
        if not significant:
            return "No statistically significant difference in engagement between collective and individual language."
        elif lift > 50:
            return "STRONG movement signal: Collective language drives significantly higher engagement."
        elif lift > 20:
            return "MODERATE movement signal: Collective language shows elevated engagement."
        elif lift > 0:
            return "WEAK movement signal: Slight engagement advantage with collective language."
        else:
            return "NO movement signal: Individual language performs as well or better."

    def _interpret_iri(self, frequency: float, score: float) -> str:
        """Interpret Identity Resonance Index."""
        if frequency > 0.3:
            return "STRONG identity resonance: Over 30% of posts express identity alignment."
        elif frequency > 0.15:
            return "MODERATE identity resonance: Significant portion expresses feeling seen/represented."
        elif frequency > 0.05:
            return "WEAK identity resonance: Some identity alignment present."
        else:
            return "MINIMAL identity resonance: Rare mentions of representation."

    def _interpret_er(self, ratio: float) -> str:
        """Interpret Evangelism Ratio."""
        if ratio > 0.4:
            return "STRONG evangelism: Over 40% of posts urge others to attend."
        elif ratio > 0.2:
            return "MODERATE evangelism: Significant recommendation activity."
        elif ratio > 0.1:
            return "WEAK evangelism: Some urging others to see show."
        else:
            return "MINIMAL evangelism: Low recommendation rate."

    def _interpret_ras(self, ratio: float) -> str:
        """Interpret Repeat Attendance Signal."""
        if ratio > 0.3:
            return "STRONG repeat signal: Over 30% mention multiple viewings."
        elif ratio > 0.15:
            return "MODERATE repeat signal: Notable repeat attendance mentions."
        elif ratio > 0.05:
            return "WEAK repeat signal: Some repeat viewing mentions."
        else:
            return "MINIMAL repeat signal: Rare repeat attendance mentions."

    def _interpret_bis(self, frequency: float, intensity: float) -> str:
        """Interpret Belonging Intensity Score."""
        if frequency > 0.4 and intensity > 2:
            return "STRONG belonging signal: High frequency and intensity of belonging language."
        elif frequency > 0.2 or intensity > 1.5:
            return "MODERATE belonging signal: Notable belonging expressions."
        elif frequency > 0.1:
            return "WEAK belonging signal: Some belonging language present."
        else:
            return "MINIMAL belonging signal: Rare belonging expressions."

    def _interpret_gim(self, frequency: float) -> str:
        """Interpret Gatekeeping & Insider Markers."""
        if frequency > 0.25:
            return "STRONG insider culture: High gatekeeping/insider language."
        elif frequency > 0.1:
            return "MODERATE insider culture: Notable insider markers."
        elif frequency > 0.05:
            return "WEAK insider culture: Some insider references."
        else:
            return "MINIMAL insider culture: Rare gatekeeping language."

    def _interpret_cfs(self, frequency: float, rush: int, lottery: int) -> str:
        """Interpret Community Formation Signals."""
        if frequency > 0.2 or (rush + lottery) > 20:
            return "STRONG community formation: Clear evidence of organized fan communities."
        elif frequency > 0.1 or (rush + lottery) > 10:
            return "MODERATE community formation: Some community organization evident."
        elif frequency > 0.05:
            return "WEAK community formation: Limited community references."
        else:
            return "MINIMAL community formation: Rare community mentions."

    def _interpret_mpi(self, viral: int, total: int) -> str:
        """Interpret Mimetic Propagation Index."""
        ratio = viral / total if total > 0 else 0
        if ratio > 0.1:
            return "STRONG mimetic spread: High variance suggests viral content."
        elif ratio > 0.05:
            return "MODERATE mimetic spread: Some viral patterns detected."
        else:
            return "WEAK mimetic spread: Limited viral propagation."

    def _interpret_overall_cmm(self, score: float) -> str:
        """Interpret overall CMM score."""
        if score >= 70:
            return "DEFINITIVE MOVEMENT: Oh Mary! exhibits strong Cultural Movement Marketing characteristics. Audiences speak as if this is a movement, not just entertainment."
        elif score >= 50:
            return "STRONG MOVEMENT SIGNALS: Oh Mary! shows clear CMM patterns. Audiences demonstrate movement-like behaviors and identity attachment."
        elif score >= 30:
            return "MODERATE MOVEMENT POTENTIAL: Oh Mary! has some CMM characteristics. Some movement behaviors present but not dominant."
        else:
            return "LIMITED MOVEMENT CHARACTERISTICS: Oh Mary! functions primarily as entertainment. Little evidence of movement-like audience behavior."

    def _categorize_cmm_level(self, score: float) -> str:
        """Categorize CMM level."""
        if score >= 70:
            return "DEFINITIVE_MOVEMENT"
        elif score >= 50:
            return "STRONG_MOVEMENT"
        elif score >= 30:
            return "MODERATE_MOVEMENT"
        else:
            return "LIMITED_MOVEMENT"
