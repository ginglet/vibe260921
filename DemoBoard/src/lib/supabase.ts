import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseServiceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";

if (!supabaseUrl || !supabaseServiceRoleKey) {
  throw new Error(
    "Supabase environment variables not set. Please add NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to .env.local"
  );
}

// Singleton Supabase client for server-side operations
// Uses service role key to bypass RLS (row-level security)
const globalForSupabase = globalThis as unknown as {
  __supabaseClient?: ReturnType<typeof createClient<any, "public", any>>;
};

function getSupabaseClient() {
  if (!globalForSupabase.__supabaseClient) {
    globalForSupabase.__supabaseClient = createClient(
      supabaseUrl,
      supabaseServiceRoleKey,
      {
        auth: {
          persistSession: false, // Server-side only, no session persistence
          autoRefreshToken: false,
          detectSessionInUrl: false,
        },
      }
    );
  }
  return globalForSupabase.__supabaseClient;
}

export const supabase = getSupabaseClient();
