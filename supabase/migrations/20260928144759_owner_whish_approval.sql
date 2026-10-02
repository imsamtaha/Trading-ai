CREATE UNIQUE INDEX IF NOT EXISTS atlas_user_subscriptions_billing_reference_unique ON public.atlas_user_subscriptions (billing_reference) WHERE billing_reference IS NOT NULL;
CREATE OR REPLACE FUNCTION public.atlas_approve_whish_subscription(target_user_id uuid, selected_plan text, payment_reference text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  IF auth.uid() IS NULL OR NOT EXISTS (
    SELECT 1 FROM auth.users WHERE id = auth.uid() AND lower(email) = 'imsamtaha.ai@gmail.com' AND email_confirmed_at IS NOT NULL
  ) THEN
    RAISE EXCEPTION 'Owner approval required' USING ERRCODE = '42501';
  END IF;
  IF upper(selected_plan) NOT IN ('STARTER', 'PRO', 'ELITE')
    OR payment_reference !~ '^ATLAS-[A-F0-9]{24}$'
    OR NOT EXISTS (SELECT 1 FROM auth.users WHERE id = target_user_id)
  THEN
    RAISE EXCEPTION 'Invalid subscription approval' USING ERRCODE = '22023';
  END IF;
  INSERT INTO public.atlas_user_subscriptions (user_id, plan, status, billing_reference, expires_at)
  VALUES (target_user_id, upper(selected_plan), 'ACTIVE', payment_reference, now() + interval '30 days')
  ON CONFLICT (user_id) DO UPDATE SET
    plan = EXCLUDED.plan, status = EXCLUDED.status,
    billing_reference = EXCLUDED.billing_reference, expires_at = EXCLUDED.expires_at;
END;
$$;
REVOKE ALL ON FUNCTION public.atlas_approve_whish_subscription(uuid, text, text) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.atlas_approve_whish_subscription(uuid, text, text) TO authenticated;
