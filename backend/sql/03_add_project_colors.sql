-- Add color columns to projects table
ALTER TABLE projects ADD COLUMN color VARCHAR(7) NOT NULL DEFAULT '#000000';
ALTER TABLE projects ADD COLUMN extra_color VARCHAR(7);

-- Set color values for each project
UPDATE projects SET color = '#8a07db' WHERE name = 'Computer games';
UPDATE projects SET color = '#f52020' WHERE name = 'YouTube';
UPDATE projects SET color = '#f59120' WHERE name = 'Running';
UPDATE projects SET color = '#f59120', extra_color = '#fccd97' WHERE name = 'Fast walking';
UPDATE projects SET color = '#07db9b' WHERE name = 'Films';
UPDATE projects SET color = '#9fdb07' WHERE name = 'Podcasts';
UPDATE projects SET color = '#2e2e2e' WHERE name = 'Vibe coding';
UPDATE projects SET color = '#20c7f5' WHERE name = 'Telegram channel';
UPDATE projects SET color = '#068a19' WHERE name = 'Reading fiction';
UPDATE projects SET color = '#068a19', extra_color = '#07dbad' WHERE name = 'Reading tech books';
UPDATE projects SET color = '#068a19', extra_color = '#98db07' WHERE name = 'Reading non-fiction';
UPDATE projects SET color = '#f5ee20' WHERE name = 'English';
UPDATE projects SET color = '#7797c9' WHERE name = 'Diary';
UPDATE projects SET color = '#2055f5' WHERE name = 'Meatings';
UPDATE projects SET color = '#f59120', extra_color = '#fae7d2' WHERE name = 'Slow walking';
UPDATE projects SET color = '#db076a' WHERE name = 'Growth sessions';

-- Fix typo: Meatings -> Meetings
UPDATE projects SET name = 'Meetings' WHERE name = 'Meatings';

