#!/usr/bin/env python3
"""
Wasteless.io - FastAPI Backend
==============================

Fast, lightweight API for cloud cost optimization dashboard.
Replaces Streamlit for better performance.

Author: Wasteless Team
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

# Configure logging for scheduler
logging.getLogger('apscheduler').setLevel(logging.WARNING)

# Load environment variables
APP_DIR = Path(__file__).parent
ENV_PATH = APP_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'wasteless'),
    'user': os.getenv('DB_USER', 'wasteless'),
    'password': os.getenv('DB_PASSWORD', '')
}


def get_db():
    """Get database connection."""
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def sync_aws_job():
    """Background job to sync recommendations with AWS state."""
    try:
        import boto3
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        cursor = conn.cursor()

        # Get pending recommendations
        cursor.execute("""
            SELECT DISTINCT w.resource_id
            FROM recommendations r
            JOIN waste_detected w ON r.waste_id = w.id
            WHERE r.status = 'pending'
        """)
        pending_instances = [row['resource_id'] for row in cursor.fetchall()]

        if not pending_instances:
            conn.close()
            return

        # Check AWS for instance states
        regions = ['eu-west-1', 'eu-west-2', 'eu-west-3', 'us-east-1']
        aws_states = {}

        for region in regions:
            try:
                ec2 = boto3.client('ec2', region_name=region)
                response = ec2.describe_instances(
                    Filters=[{'Name': 'instance-id', 'Values': pending_instances}]
                )
                for reservation in response.get('Reservations', []):
                    for instance in reservation.get('Instances', []):
                        aws_states[instance['InstanceId']] = instance['State']['Name']
            except Exception:
                continue

        # Mark obsolete recommendations
        obsolete_count = 0
        for instance_id in pending_instances:
            state = aws_states.get(instance_id)

            if state is None or state == 'terminated':
                cursor.execute("""
                    UPDATE recommendations r
                    SET status = 'obsolete', applied_at = NOW()
                    FROM waste_detected w
                    WHERE r.waste_id = w.id
                    AND w.resource_id = %s
                    AND r.status = 'pending'
                """, (instance_id,))
                obsolete_count += cursor.rowcount

        conn.commit()
        conn.close()

        if obsolete_count > 0:
            print(f"🔄 Auto-sync: marked {obsolete_count} recommendations as obsolete")

    except Exception as e:
        print(f"⚠️ Auto-sync error: {e}")


# Scheduler instance
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup: test database connection
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        print("✅ Database connection OK")
    except Exception as e:
        print(f"⚠️ Database connection failed: {e}")

    # Start scheduler for auto-sync (every 5 minutes)
    scheduler.add_job(sync_aws_job, 'interval', minutes=5, id='aws_sync')
    scheduler.start()
    print("🔄 Auto-sync scheduler started (every 5 min)")

    yield

    # Shutdown
    scheduler.shutdown()
    print("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Wasteless.io",
    description="Cloud Cost Optimization Platform",
    version="2.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

# Templates
templates = Jinja2Templates(directory=APP_DIR / "templates")

# Add datetime to template globals for time calculations
from datetime import datetime
templates.env.globals['now'] = datetime.now

# Add config_manager to template globals for mode badge
from utils.config_manager import ConfigManager
_config_manager = ConfigManager()
templates.env.globals['get_dry_run'] = _config_manager.get_dry_run


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ActionRequest(BaseModel):
    """Request to execute actions on recommendations."""
    recommendation_ids: List[int]
    action: str  # 'approve', 'reject', 'execute'
    dry_run: bool = True


class ConfigUpdate(BaseModel):
    """Configuration update request."""
    key: str
    value: str | int | float | bool


# =============================================================================
# HTML PAGES
# =============================================================================

@app.get("/landing", response_class=HTMLResponse)
async def landing(request: Request):
    """Public landing page."""
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, conn=Depends(get_db)):
    """Home page with overview metrics."""
    cursor = conn.cursor()

    # Fetch metrics in single query
    cursor.execute("""
        WITH metrics AS (
            SELECT
                COALESCE(SUM(estimated_monthly_savings_eur), 0) as potential_savings,
                COUNT(*) FILTER (WHERE status = 'pending') as pending_count
            FROM recommendations
        ),
        actions AS (
            SELECT COUNT(*) as success_count
            FROM actions_log
            WHERE action_status = 'success'
        )
        SELECT
            m.potential_savings,
            m.pending_count,
            a.success_count
        FROM metrics m
        CROSS JOIN actions a;
    """)
    result = cursor.fetchone()

    # Recent waste
    cursor.execute("""
        SELECT resource_id, waste_type, monthly_waste_eur, confidence_score, created_at
        FROM waste_detected
        ORDER BY created_at DESC
        LIMIT 5
    """)
    recent_waste = cursor.fetchall()

    # Recent actions
    cursor.execute("""
        SELECT resource_id, action_type, action_status, action_date
        FROM actions_log
        ORDER BY action_date DESC
        LIMIT 5
    """)
    recent_actions = cursor.fetchall()

    cursor.close()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "metrics": result,
        "recent_waste": recent_waste,
        "recent_actions": recent_actions
    })


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, conn=Depends(get_db)):
    """Executive dashboard with KPIs and charts."""
    cursor = conn.cursor()

    # Fetch KPIs including new CTO metrics
    cursor.execute("""
        WITH metrics AS (
            SELECT COALESCE(SUM(estimated_monthly_savings_eur), 0) as potential_monthly
            FROM recommendations WHERE status = 'pending'
        ),
        savings AS (
            SELECT COALESCE(SUM(actual_savings_eur), 0) as verified_savings
            FROM savings_realized
        ),
        waste AS (
            SELECT COUNT(*) as waste_count FROM waste_detected
        ),
        actions AS (
            SELECT
                COUNT(CASE WHEN action_status='success' THEN 1 END)::float /
                NULLIF(COUNT(*), 0) * 100 as success_rate
            FROM actions_log
        ),
        cumulative AS (
            SELECT COALESCE(SUM(actual_savings_eur), 0) as total_saved
            FROM savings_realized
        ),
        inaction_cost AS (
            SELECT
                COALESCE(SUM(estimated_monthly_savings_eur), 0) as pending_savings,
                MIN(created_at) as oldest_pending
            FROM recommendations
            WHERE status = 'pending'
        ),
        last_scan AS (
            SELECT MAX(created_at) as last_analysis
            FROM waste_detected
        )
        SELECT
            m.potential_monthly,
            s.verified_savings,
            w.waste_count,
            COALESCE(a.success_rate, 0) as success_rate,
            c.total_saved as cumulative_savings,
            i.pending_savings,
            EXTRACT(DAY FROM NOW() - i.oldest_pending) as days_pending,
            l.last_analysis
        FROM metrics m
        CROSS JOIN savings s
        CROSS JOIN waste w
        CROSS JOIN actions a
        CROSS JOIN cumulative c
        CROSS JOIN inaction_cost i
        CROSS JOIN last_scan l;
    """)
    kpis = cursor.fetchone()

    # Waste trend (last 90 days for better historical context)
    cursor.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count, SUM(monthly_waste_eur) as total_waste
        FROM waste_detected
        WHERE created_at >= NOW() - INTERVAL '90 days'
        GROUP BY DATE(created_at)
        ORDER BY date
    """)
    waste_trend = cursor.fetchall()

    # Recommendations by type
    cursor.execute("""
        SELECT recommendation_type, COUNT(*) as count
        FROM recommendations
        WHERE status = 'pending'
        GROUP BY recommendation_type
    """)
    rec_by_type = cursor.fetchall()

    cursor.close()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "kpis": kpis,
        "waste_trend": waste_trend,
        "rec_by_type": rec_by_type
    })


@app.get("/recommendations", response_class=HTMLResponse)
async def recommendations(
    request: Request,
    conn=Depends(get_db),
    type_filter: str = "All",
    min_savings: int = 0,
    min_confidence: float = 0.0
):
    """Recommendations management page."""
    cursor = conn.cursor()

    # Build query with filters
    query = """
        SELECT
            r.id,
            r.recommendation_type,
            w.resource_id,
            r.estimated_monthly_savings_eur,
            w.confidence_score,
            r.action_required,
            r.status,
            r.created_at,
            w.metadata->>'instance_type' as instance_type,
            (w.metadata->>'cpu_avg_7d')::numeric as cpu_avg,
            (w.metadata->>'monthly_cost_eur')::numeric as monthly_cost,
            w.metadata->>'instance_state' as instance_state
        FROM recommendations r
        JOIN waste_detected w ON r.waste_id = w.id
        WHERE r.status = 'pending'
    """
    params = []

    if type_filter != "All":
        query += " AND r.recommendation_type = %s"
        params.append(type_filter)

    if min_savings > 0:
        query += " AND r.estimated_monthly_savings_eur >= %s"
        params.append(min_savings)

    if min_confidence > 0:
        query += " AND w.confidence_score >= %s"
        params.append(min_confidence)

    query += " ORDER BY r.estimated_monthly_savings_eur DESC LIMIT 500"

    cursor.execute(query, params if params else None)
    recommendations = cursor.fetchall()

    # Summary stats
    total_savings = sum(r['estimated_monthly_savings_eur'] or 0 for r in recommendations)
    avg_confidence = sum(r['confidence_score'] or 0 for r in recommendations) / len(recommendations) if recommendations else 0

    cursor.close()

    return templates.TemplateResponse("recommendations.html", {
        "request": request,
        "recommendations": recommendations,
        "total_savings": total_savings,
        "avg_confidence": avg_confidence,
        "type_filter": type_filter,
        "min_savings": min_savings,
        "min_confidence": min_confidence
    })


@app.get("/history", response_class=HTMLResponse)
async def history(
    request: Request,
    conn=Depends(get_db),
    status_filter: str = "All",
    action_filter: str = "All",
    days_back: int = 30
):
    """Action history and audit trail."""
    cursor = conn.cursor()

    query = """
        SELECT
            a.id,
            a.resource_id,
            a.action_type,
            a.action_status,
            a.dry_run,
            a.action_date,
            a.error_message,
            a.executed_by,
            r.estimated_monthly_savings_eur
        FROM actions_log a
        LEFT JOIN recommendations r ON a.recommendation_id = r.id
        WHERE a.action_date >= NOW() - INTERVAL '%s days'
    """
    params = [days_back]

    if status_filter != "All":
        query += " AND a.action_status = %s"
        params.append(status_filter)

    if action_filter != "All":
        query += " AND a.action_type = %s"
        params.append(action_filter)

    query += " ORDER BY a.action_date DESC LIMIT 100"

    cursor.execute(query, tuple(params))
    actions = cursor.fetchall()

    # Summary
    success_count = sum(1 for a in actions if a['action_status'] == 'success')
    failed_count = sum(1 for a in actions if a['action_status'] == 'failed')
    total_savings = sum(a['estimated_monthly_savings_eur'] or 0 for a in actions)

    cursor.close()

    return templates.TemplateResponse("history.html", {
        "request": request,
        "actions": actions,
        "success_count": success_count,
        "failed_count": failed_count,
        "total_savings": total_savings,
        "status_filter": status_filter,
        "action_filter": action_filter,
        "days_back": days_back
    })


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, conn=Depends(get_db)):
    """Settings and configuration page."""
    from utils.config_manager import ConfigManager

    config_manager = ConfigManager()
    config = config_manager.load_config()

    # Database stats
    cursor = conn.cursor()
    cursor.execute("""
        WITH counts AS (
            SELECT
                (SELECT COUNT(*) FROM ec2_metrics) as ec2_metrics,
                (SELECT COUNT(*) FROM waste_detected) as waste_detected,
                (SELECT COUNT(*) FROM recommendations) as recommendations,
                (SELECT COUNT(*) FROM actions_log) as actions_log,
                (SELECT COUNT(*) FROM savings_realized) as savings_realized
        )
        SELECT * FROM counts;
    """)
    stats = cursor.fetchone()
    cursor.close()

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "config": config,
        "stats": stats
    })


@app.get("/cloud-resources", response_class=HTMLResponse)
async def cloud_resources(
    request: Request,
    state_filter: str = Query("all"),
    region_filter: str = Query("all")
):
    """Cloud resources inventory page - shows all EC2 instances."""
    import boto3

    regions = ['eu-west-1', 'eu-west-2', 'eu-west-3', 'us-east-1']
    instances = []

    for region in regions:
        try:
            ec2 = boto3.client('ec2', region_name=region)
            response = ec2.describe_instances()
            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    # Extract Name tag
                    name = ''
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name':
                            name = tag['Value']
                            break

                    instances.append({
                        'instance_id': instance['InstanceId'],
                        'name': name or '-',
                        'type': instance['InstanceType'],
                        'state': instance['State']['Name'],
                        'region': region,
                        'launch_time': instance.get('LaunchTime'),
                        'public_ip': instance.get('PublicIpAddress', '-'),
                        'private_ip': instance.get('PrivateIpAddress', '-')
                    })
        except Exception as e:
            print(f"Error fetching instances from {region}: {e}")

    # Apply filters
    if state_filter != 'all':
        instances = [i for i in instances if i['state'] == state_filter]
    if region_filter != 'all':
        instances = [i for i in instances if i['region'] == region_filter]

    # Sort by state (running first) then name
    instances.sort(key=lambda x: (x['state'] != 'running', x['name']))

    return templates.TemplateResponse("cloud_resources.html", {
        "request": request,
        "instances": instances,
        "state_filter": state_filter,
        "region_filter": region_filter,
        "regions": regions,
        "total_count": len(instances),
        "running_count": len([i for i in instances if i['state'] == 'running']),
        "stopped_count": len([i for i in instances if i['state'] == 'stopped'])
    })


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/api/metrics")
async def api_metrics(conn=Depends(get_db)):
    """Get dashboard metrics as JSON."""
    cursor = conn.cursor()
    cursor.execute("""
        WITH metrics AS (
            SELECT
                COALESCE(SUM(estimated_monthly_savings_eur), 0) as potential_savings,
                COUNT(*) FILTER (WHERE status = 'pending') as pending_count
            FROM recommendations
        ),
        actions AS (
            SELECT COUNT(*) as success_count
            FROM actions_log
            WHERE action_status = 'success'
        )
        SELECT m.potential_savings, m.pending_count, a.success_count
        FROM metrics m CROSS JOIN actions a;
    """)
    result = cursor.fetchone()
    cursor.close()

    return {
        "potential_savings": float(result['potential_savings']),
        "pending_count": int(result['pending_count']),
        "actions_count": int(result['success_count'])
    }


@app.get("/api/recommendations")
async def api_recommendations(
    conn=Depends(get_db),
    type_filter: str = "All",
    min_savings: int = 0,
    min_confidence: float = 0.0,
    limit: int = 100
):
    """Get recommendations as JSON."""
    cursor = conn.cursor()

    query = """
        SELECT
            r.id,
            r.recommendation_type,
            w.resource_id,
            r.estimated_monthly_savings_eur,
            w.confidence_score,
            r.action_required,
            r.status,
            r.created_at,
            w.metadata->>'instance_type' as instance_type
        FROM recommendations r
        JOIN waste_detected w ON r.waste_id = w.id
        WHERE r.status = 'pending'
    """
    params = []

    if type_filter != "All":
        query += " AND r.recommendation_type = %s"
        params.append(type_filter)

    if min_savings > 0:
        query += " AND r.estimated_monthly_savings_eur >= %s"
        params.append(min_savings)

    if min_confidence > 0:
        query += " AND w.confidence_score >= %s"
        params.append(min_confidence)

    query += f" ORDER BY r.estimated_monthly_savings_eur DESC LIMIT {limit}"

    cursor.execute(query, params if params else None)
    results = cursor.fetchall()
    cursor.close()

    return {"recommendations": results, "count": len(results)}


@app.post("/api/actions")
async def api_execute_actions(action_request: ActionRequest, conn=Depends(get_db)):
    """Execute actions on recommendations."""
    cursor = conn.cursor()
    results = []

    for rec_id in action_request.recommendation_ids:
        try:
            if action_request.action == "reject":
                # Reject recommendation
                cursor.execute("""
                    UPDATE recommendations
                    SET status = 'rejected', applied_at = NOW()
                    WHERE id = %s
                    RETURNING id
                """, (rec_id,))
                result = cursor.fetchone()
                results.append({
                    "recommendation_id": rec_id,
                    "success": result is not None,
                    "action": "rejected"
                })

            elif action_request.action in ("approve", "execute"):
                # Get instance info
                cursor.execute("""
                    SELECT w.resource_id, r.recommendation_type
                    FROM recommendations r
                    JOIN waste_detected w ON r.waste_id = w.id
                    WHERE r.id = %s
                """, (rec_id,))
                row = cursor.fetchone()

                if row:
                    instance_id = row['resource_id']
                    rec_type = row['recommendation_type']
                    action_type = rec_type.replace('_instance', '')
                    aws_success = True
                    aws_error = None

                    # Execute real AWS action if NOT in dry-run mode
                    if not action_request.dry_run:
                        try:
                            import boto3
                            # Try multiple regions to find the instance
                            regions = ['eu-west-1', 'eu-west-2', 'eu-west-3', 'us-east-1']
                            executed = False

                            for region in regions:
                                try:
                                    ec2 = boto3.client('ec2', region_name=region)

                                    # Check if instance exists in this region
                                    response = ec2.describe_instances(
                                        Filters=[{'Name': 'instance-id', 'Values': [instance_id]}]
                                    )

                                    if response['Reservations']:
                                        # Instance found in this region
                                        instance_state = response['Reservations'][0]['Instances'][0]['State']['Name']
                                        print(f"Found instance {instance_id} in {region}, state: {instance_state}")

                                        if instance_state in ['terminated', 'shutting-down']:
                                            print(f"Instance {instance_id} already terminated/shutting-down")
                                            executed = True
                                            break

                                        if rec_type == 'stop_instance':
                                            ec2.stop_instances(InstanceIds=[instance_id])
                                            print(f"✅ Stopped instance {instance_id} in {region}")
                                        elif rec_type == 'terminate_instance':
                                            ec2.terminate_instances(InstanceIds=[instance_id])
                                            print(f"✅ Terminated instance {instance_id} in {region}")
                                        executed = True
                                        break
                                except Exception as e:
                                    print(f"Region {region} error: {e}")
                                    continue

                            if not executed:
                                aws_success = False
                                aws_error = f"Instance {instance_id} not found in any region"

                        except ImportError:
                            aws_success = False
                            aws_error = "boto3 not installed"
                        except Exception as e:
                            aws_success = False
                            aws_error = str(e)

                    # Log action
                    action_status = 'success' if (action_request.dry_run or aws_success) else 'failed'
                    cursor.execute("""
                        INSERT INTO actions_log
                        (resource_id, recommendation_id, resource_type, action_type, action_status, dry_run, action_date, error_message)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
                        RETURNING id
                    """, (
                        instance_id,
                        rec_id,
                        'ec2_instance',
                        action_type,
                        action_status,
                        action_request.dry_run,
                        aws_error
                    ))

                    # Update recommendation status
                    new_status = 'approved' if (action_request.dry_run or aws_success) else 'pending'
                    cursor.execute("""
                        UPDATE recommendations
                        SET status = %s, applied_at = NOW()
                        WHERE id = %s
                    """, (new_status, rec_id))

                    result_entry = {
                        "recommendation_id": rec_id,
                        "instance_id": instance_id,
                        "success": action_request.dry_run or aws_success,
                        "dry_run": action_request.dry_run,
                        "action": rec_type
                    }
                    if aws_error:
                        result_entry["error"] = aws_error
                    results.append(result_entry)
                else:
                    results.append({
                        "recommendation_id": rec_id,
                        "success": False,
                        "error": "Recommendation not found"
                    })

        except Exception as e:
            results.append({
                "recommendation_id": rec_id,
                "success": False,
                "error": str(e)
            })

    conn.commit()
    cursor.close()

    return {"results": results}


@app.post("/api/config")
async def api_update_config(update: ConfigUpdate):
    """Update configuration value."""
    from utils.config_manager import ConfigManager

    config_manager = ConfigManager()

    try:
        if update.key == "auto_remediation_enabled":
            success = config_manager.set_auto_remediation_enabled(update.value)
        elif update.key == "dry_run_days":
            success = config_manager.set_dry_run_days(update.value)
        elif update.key == "dry_run":
            success = config_manager.set_dry_run(update.value)
        else:
            success = config_manager.update_protection_rule(update.key, update.value)

        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/whitelist")
async def api_whitelist(instance_id: str, action: str = "add"):
    """Add or remove instance from whitelist."""
    from utils.config_manager import ConfigManager

    config_manager = ConfigManager()

    try:
        if action == "add":
            success = config_manager.add_instance_to_whitelist(instance_id)
        else:
            success = config_manager.remove_instance_from_whitelist(instance_id)

        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/sync-aws")
async def api_sync_aws(conn=Depends(get_db)):
    """Synchronize recommendations with current AWS instance states."""
    import traceback

    try:
        import boto3
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"boto3 not installed: {e}")

    try:
        cursor = conn.cursor()

        # Get all pending recommendations with their instance IDs
        cursor.execute("""
            SELECT DISTINCT w.resource_id
            FROM recommendations r
            JOIN waste_detected w ON r.waste_id = w.id
            WHERE r.status = 'pending'
        """)
        pending_instances = [row['resource_id'] for row in cursor.fetchall()]

        if not pending_instances:
            return {"synced": 0, "obsolete": 0, "message": "No pending recommendations"}

        # Query AWS for instance states (check multiple regions)
        regions_to_check = ['eu-west-1', 'eu-west-2', 'eu-west-3', 'us-east-1']
        aws_states = {}

        for region in regions_to_check:
            try:
                ec2 = boto3.client('ec2', region_name=region)
                # Use filters instead of InstanceIds to avoid errors for non-existent instances
                response = ec2.describe_instances(
                    Filters=[{'Name': 'instance-id', 'Values': pending_instances}]
                )
                for reservation in response.get('Reservations', []):
                    for instance in reservation.get('Instances', []):
                        aws_states[instance['InstanceId']] = {
                            'state': instance['State']['Name'],
                            'region': region
                        }
            except Exception as e:
                # Log error but continue with other regions
                print(f"Error checking region {region}: {e}")
                continue

        # Update recommendations based on AWS state
        obsolete_count = 0
        synced_count = 0

        for instance_id in pending_instances:
            aws_info = aws_states.get(instance_id)

            if aws_info is None:
                # Instance doesn't exist - mark as obsolete
                cursor.execute("""
                    UPDATE recommendations r
                    SET status = 'obsolete', applied_at = NOW()
                    FROM waste_detected w
                    WHERE r.waste_id = w.id
                    AND w.resource_id = %s
                    AND r.status = 'pending'
                """, (instance_id,))
                obsolete_count += cursor.rowcount
            else:
                aws_state = aws_info['state']

                # Check if recommendation is still valid
                cursor.execute("""
                    SELECT r.id, r.recommendation_type
                    FROM recommendations r
                    JOIN waste_detected w ON r.waste_id = w.id
                    WHERE w.resource_id = %s AND r.status = 'pending'
                """, (instance_id,))

                for rec in cursor.fetchall():
                    rec_type = rec['recommendation_type']
                    should_obsolete = False

                    # Stop recommendation but instance already stopped/terminated
                    if rec_type == 'stop_instance' and aws_state in ('stopped', 'terminated'):
                        should_obsolete = True
                    # Terminate recommendation but instance already terminated
                    elif rec_type == 'terminate_instance' and aws_state == 'terminated':
                        should_obsolete = True

                    if should_obsolete:
                        cursor.execute("""
                            UPDATE recommendations
                            SET status = 'obsolete', applied_at = NOW()
                            WHERE id = %s
                        """, (rec['id'],))
                        obsolete_count += 1
                    else:
                        # Update the stored state in waste_detected metadata
                        cursor.execute("""
                            UPDATE waste_detected
                            SET metadata = jsonb_set(
                                COALESCE(metadata, '{}'::jsonb),
                                '{instance_state}',
                                %s::jsonb
                            )
                            WHERE resource_id = %s
                        """, (f'"{aws_state}"', instance_id))
                        synced_count += 1

        conn.commit()

        return {
            "synced": synced_count,
            "obsolete": obsolete_count,
            "total_checked": len(pending_instances),
            "message": f"Synced {synced_count} instances, marked {obsolete_count} as obsolete"
        }

    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"Sync AWS error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# =============================================================================
# RUN SERVER
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('STREAMLIT_SERVER_PORT', '8888'))
    uvicorn.run(app, host="0.0.0.0", port=port)
