-- Solution for the SQL Coding Challenge
-- Task: Generate a list of places which have strictly more 'recommended' than 'not recommended' opinions.
-- Ordering: Alphabetical by place name.

SELECT place
FROM opinions
GROUP BY place
HAVING COUNT(CASE WHEN opinion = 'recommended' THEN 1 END) > COUNT(CASE WHEN opinion = 'not recommended' THEN 1 END)
ORDER BY place;
