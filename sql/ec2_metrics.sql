-- ============================================
-- Migration 001: Add EC2 Metrics Table
-- Description: Store CloudWatch metrics for EC2 instances
-- Author: Wasteless
-- Date: 2025-01-XX
-- ============================================

-- Create ec2_metrics table
CREATE TABLE IF NOT EXISTS ec2_metrics (
    id SERIAL PRIMARY KEY,
    instance_id VARCHAR(50) NOT NULL,
    instance_type VARCHAR(50),
    instance_state VARCHAR(20),
    launch_time TIMESTAMP,
    metric_date DATE NOT NULL,
    avg_cpu_percent DECIMAL(5, 2),
    max_cpu_percent DECIMAL(5, 2),
    min_cpu_percent DECIMAL(5, 2),
    avg_network_in_mb DECIMAL(10, 2),
    avg_network_out_mb DECIMAL(10, 2),
    tags JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_ec2_metrics_instance ON ec2_metrics(instance_id);
CREATE INDEX idx_ec2_metrics_date ON ec2_metrics(metric_date);
CREATE INDEX idx_ec2_metrics_instance_date ON ec2_metrics(instance_id, metric_date);

-- Add comments for documentation
COMMENT ON TABLE ec2_metrics IS 'CloudWatch metrics for EC2 instances over time';
COMMENT ON COLUMN ec2_metrics.instance_id IS 'AWS EC2 instance ID (e.g., i-0abc123...)';
COMMENT ON COLUMN ec2_metrics.avg_cpu_percent IS 'Average CPU utilization over 24 hours (0-100)';
COMMENT ON COLUMN ec2_metrics.tags IS 'Instance tags in JSON format';

-- Create update trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_ec2_metrics_updated_at 
    BEFORE UPDATE ON ec2_metrics 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 001 completed successfully';
    RAISE NOTICE '   - Table ec2_metrics created';
    RAISE NOTICE '   - 3 indexes created';
    RAISE NOTICE '   - Update trigger created';
END $$;