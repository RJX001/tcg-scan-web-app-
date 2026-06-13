"use client";

import { useAuth } from "@clerk/nextjs";
import { setAuthTokenGetter } from "@tcgscan/sdk-ts";
import { useEffect } from "react";

export function AuthBridge() {
  const { getToken } = useAuth();
  useEffect(() => {
    setAuthTokenGetter(() => getToken());
  }, [getToken]);
  return null;
}
