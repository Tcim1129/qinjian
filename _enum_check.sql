SELECT t.typname, e.enumlabel
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname IN ('reporttype','reportstatus','pairstatus','pairtype')
ORDER BY t.typname, e.enumsortorder;
