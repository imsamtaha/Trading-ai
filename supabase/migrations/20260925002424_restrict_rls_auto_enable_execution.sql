-- Applied migration exported from Supabase history; internal event-trigger helper.
-- Keep the owner/service-role privileges and the ensure_rls event trigger intact.
REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated;
