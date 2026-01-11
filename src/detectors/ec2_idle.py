#!/usr/bin/env python3
"""
EC2 Idle Instance Detector for Wasteless

Detects EC2 instances with low CPU utilization over a period of time.
Generates waste estimates and actionable recommendations.

Detection criteria:
- Average CPU < 5% over 7 days
- Confidence score based on how close to 0% the average is

Author: Wasteless
"""

import os
import sys
from datetime import datetime, date
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
import json

# Load environment variables
load_dotenv()

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# EC2 instance pricing (EUR/month, eu-west-1)
# Source: AWS Pricing Calculator (approximate)
EC2_PRICING = {
    't2.micro': 9.50,
    't2.small': 19.00,
    't2.medium': 38.00,
    't3.micro': 8.50,
    't3.small': 17.00,
    't3.medium': 34.00,
    't3.large': 68.00,
    't3.xlarge': 136.00,
    't3.2xlarge': 272.00,
    'm5.large': 96.00,
    'm5.xlarge': 192.00,
    'm5.2xlarge': 384.00,
    'c5.large': 85.00,
    'c5.xlarge': 170.00,
    'r5.large': 126.00,
    'r5.xlarge': 252.00,
}


class EC2IdleDetector:
    """Detect idle EC2 instances based on CPU utilization."""

    def __init__(self):
        """Initialize detector with database connection."""
        logger.info("Initializing EC2 Idle Detector")

        # Verify database credentials
        db_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing = [var for var in db_vars if not os.getenv(var)]
        if missing:
            logger.error(f"Missing database variables: {', '.join(missing)}")
            sys.exit(1)

        # Initialize database connection
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST'),
                port=int(os.getenv('DB_PORT')),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD')
            )
            logger.info("✅ Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)

    def get_instance_monthly_cost(self, instance_type):
        """
        Get monthly cost for EC2 instance type.

        Args:
            instance_type (str): EC2 instance type (e.g., 't3.medium')

        Returns:
            float: Monthly cost in EUR, or default 50 EUR if not found
        """
        cost = EC2_PRICING.get(instance_type, 50.0)
        if instance_type not in EC2_PRICING:
            logger.warning(f"Pricing not found for {instance_type}, using default €50/month")
        return cost

    def detect_idle_instances(self, cpu_threshold=5.0, days=7):
        """
        Detect EC2 instances with low CPU utilization.

        Args:
            cpu_threshold (float): CPU percentage threshold (default: 5.0%)
            days (int): Number of days to analyze (default: 7)

        Returns:
            list[dict]: List of idle instances with waste details
        """
        logger.info(f"Detecting idle instances (CPU < {cpu_threshold}%, last {days} days)...")

        cursor = self.conn.cursor()

        # Query to find instances with low CPU - adapted for current table structure
        query = """
        SELECT
            instance_id,
            instance_type,
            instance_state,
            AVG(cpu_avg) as cpu_avg_7d,
            MAX(cpu_max) as cpu_max_7d,
            MIN(cpu_avg) as cpu_min_7d,
            COUNT(*) as datapoints
        FROM ec2_metrics
        WHERE collection_date >= CURRENT_DATE - %s::interval
          AND cpu_avg IS NOT NULL
        GROUP BY instance_id, instance_type, instance_state
        HAVING AVG(cpu_avg) < %s
        ORDER BY AVG(cpu_avg) ASC;
        """

        cursor.execute(query, (f'{days} days', cpu_threshold))
        idle_instances = cursor.fetchall()

        logger.info(f"Found {len(idle_instances)} idle instances")

        # Calculate waste for each instance
        waste_list = []

        for instance in idle_instances:
            (instance_id, instance_type, instance_state,
             cpu_avg, cpu_max, cpu_min, datapoints) = instance

            # Get monthly cost
            monthly_cost = self.get_instance_monthly_cost(instance_type)

            # Calculate waste (95% of cost if idle)
            monthly_waste = round(monthly_cost * 0.95, 2)

            # Calculate confidence score
            # Closer to 0% CPU = higher confidence
            # Formula: 1.0 - (cpu_avg / threshold)
            # Examples:
            #   cpu_avg = 0.5% → confidence = 1.0 - (0.5/5.0) = 0.90
            #   cpu_avg = 2.0% → confidence = 1.0 - (2.0/5.0) = 0.60
            #   cpu_avg = 4.5% → confidence = 1.0 - (4.5/5.0) = 0.10
            confidence = round(1.0 - (float(cpu_avg) / cpu_threshold), 2)
            confidence = max(0.0, min(1.0, confidence))  # Clamp between 0-1

            waste_record = {
                'resource_id': instance_id,
                'resource_type': 'ec2_instance',
                'waste_type': 'idle_compute',
                'monthly_waste_eur': monthly_waste,
                'confidence_score': confidence,
                'metadata': {
                    'cpu_avg_7d': float(cpu_avg),
                    'cpu_max_7d': float(cpu_max),
                    'cpu_min_7d': float(cpu_min),
                    'instance_type': instance_type,
                    'instance_state': instance_state,
                    'monthly_cost_eur': monthly_cost,
                    'datapoints': datapoints,
                    'detection_method': 'cloudwatch_cpu_avg',
                    'threshold_used': cpu_threshold
                }
            }

            waste_list.append(waste_record)

            logger.info(f"  - {instance_id} ({instance_type}): "
                       f"CPU {cpu_avg:.2f}%, waste €{monthly_waste}/mo, "
                       f"confidence {confidence:.2f}")

        cursor.close()

        return waste_list

    def save_waste_detected(self, waste_list):
        """
        Save detected waste to database.

        Args:
            waste_list (list[dict]): List of waste records

        Returns:
            list[int]: List of inserted waste IDs
        """
        if not waste_list:
            logger.warning("No waste to save")
            return []

        logger.info(f"Saving {len(waste_list)} waste records to database...")

        cursor = self.conn.cursor()

        waste_ids = []
        account_id = os.getenv('AWS_ACCOUNT_ID', 'unknown')
        today = date.today()

        for waste in waste_list:
            # Insert waste record
            cursor.execute("""
                INSERT INTO waste_detected (
                    detection_date, provider, account_id, resource_id,
                    resource_type, waste_type, monthly_waste_eur,
                    confidence_score, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (
                today,
                'aws',
                account_id,
                waste['resource_id'],
                waste['resource_type'],
                waste['waste_type'],
                waste['monthly_waste_eur'],
                waste['confidence_score'],
                json.dumps(waste['metadata'])
            ))

            waste_id = cursor.fetchone()[0]
            waste_ids.append(waste_id)

        self.conn.commit()
        logger.info(f"✅ Saved {len(waste_ids)} waste records")

        cursor.close()

        return waste_ids

    def generate_recommendations(self, waste_ids):
        """
        Generate actionable recommendations for detected waste.

        Args:
            waste_ids (list[int]): List of waste record IDs

        Returns:
            int: Number of recommendations generated
        """
        if not waste_ids:
            logger.warning("No waste IDs to generate recommendations for")
            return 0

        logger.info(f"Generating recommendations for {len(waste_ids)} waste records...")

        cursor = self.conn.cursor()

        recommendations_created = 0

        for waste_id in waste_ids:
            # Get waste details
            cursor.execute("""
                SELECT resource_id, confidence_score, monthly_waste_eur, metadata
                FROM waste_detected
                WHERE id = %s;
            """, (waste_id,))

            result = cursor.fetchone()
            if not result:
                continue

            resource_id, confidence, monthly_waste, metadata_json = result
            # metadata is already a dict (JSONB type in PostgreSQL with psycopg2)
            metadata = metadata_json if isinstance(metadata_json, dict) else json.loads(metadata_json)

            cpu_avg = metadata.get('cpu_avg_7d', 0)
            instance_type = metadata.get('instance_type', 'unknown')

            # Determine recommendation type based on confidence
            if confidence >= 0.90:
                recommendation_type = 'terminate_instance'
                action = f"TERMINATE instance {resource_id} (avg CPU: {cpu_avg:.1f}%)"
            elif confidence >= 0.60:
                recommendation_type = 'stop_instance'
                action = f"STOP instance {resource_id} during off-hours (avg CPU: {cpu_avg:.1f}%)"
            else:
                recommendation_type = 'downsize_instance'
                action = f"DOWNSIZE instance {resource_id} to smaller type (avg CPU: {cpu_avg:.1f}%)"

            # Insert recommendation
            cursor.execute("""
                INSERT INTO recommendations (
                    waste_id, recommendation_type, action_required,
                    estimated_monthly_savings_eur, status
                )
                VALUES (%s, %s, %s, %s, %s);
            """, (
                waste_id,
                recommendation_type,
                action,
                monthly_waste,
                'pending'
            ))

            recommendations_created += 1

        self.conn.commit()
        logger.info(f"✅ Created {recommendations_created} recommendations")

        cursor.close()

        return recommendations_created

    def run(self, cpu_threshold=5.0, days=7):
        """
        Main orchestration method.

        Args:
            cpu_threshold (float): CPU percentage threshold
            days (int): Number of days to analyze
        """
        print("\n" + "=" * 70)
        print("🔍 EC2 IDLE INSTANCE DETECTION")
        print("=" * 70)
        print(f"CPU Threshold: < {cpu_threshold}%")
        print(f"Analysis Period: Last {days} days")
        print("=" * 70 + "\n")

        # Detect idle instances
        waste_list = self.detect_idle_instances(
            cpu_threshold=cpu_threshold,
            days=days
        )

        if not waste_list:
            print("✅ No idle instances detected!")
            print("   All instances are being utilized efficiently.")
            return

        # Calculate totals
        total_waste = sum(w['monthly_waste_eur'] for w in waste_list)
        avg_confidence = sum(w['confidence_score'] for w in waste_list) / len(waste_list)

        print(f"\n⚠️  IDLE INSTANCES DETECTED")
        print("=" * 70)
        print(f"Instances found: {len(waste_list)}")
        print(f"Total monthly waste: €{total_waste:,.2f}")
        print(f"Average confidence: {avg_confidence:.2f}")
        print("=" * 70)

        # Save to database
        waste_ids = self.save_waste_detected(waste_list)

        # Generate recommendations
        recommendations_count = self.generate_recommendations(waste_ids)

        print("\n" + "=" * 70)
        print("📊 DETECTION SUMMARY")
        print("=" * 70)
        print(f"Waste records saved: {len(waste_ids)}")
        print(f"Recommendations created: {recommendations_count}")
        print(f"Potential monthly savings: €{total_waste:,.2f}")
        print(f"Annual savings potential: €{total_waste * 12:,.2f}")
        print("=" * 70)

        print("\n✅ Detection completed successfully!")
        print("   View results in Metabase dashboards.\n")

    def __del__(self):
        """Close database connection on cleanup."""
        if hasattr(self, 'conn'):
            self.conn.close()


def main():
    """Main execution."""
    detector = EC2IdleDetector()
    detector.run(cpu_threshold=5.0, days=7)


if __name__ == '__main__':
    main()
