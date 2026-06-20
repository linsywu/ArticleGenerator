-- 014: Add description and sort_order to scenario_configs
ALTER TABLE scenario_configs ADD COLUMN description TEXT;
ALTER TABLE scenario_configs ADD COLUMN sort_order INTEGER DEFAULT 0;
