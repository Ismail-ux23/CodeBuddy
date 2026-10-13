"use client";
import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Brand from "./Brand";
import { post, safeReturn } from "@/lib/api";
export default function AuthForm({
  registering = false,
}: {
  registering?: boolean;
}) {
  const [error, setError] = useState(""),
    [visible, setVisible] = useState(false);
  const schema = z.object({
    email: z.email(),
    password: z
      .string()
      .min(registering ? 12 : 1)
      .max(128),
    display_name: registering
      ? z.string().min(1).max(100)
      : z.string().optional(),
  });
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) });
  const submit = handleSubmit(async (data) => {
    setError("");
    try {
      await post(
        `/auth/${registering ? "register" : "login"}`,
        registering ? data : { email: data.email, password: data.password },
      );
      location.assign(
        safeReturn(new URLSearchParams(location.search).get("next")),
      );
    } catch (e) {
      setError((e as Error).message);
    }
  });
  return (
    <main className="auth-page">
      <Brand />
      <div className="auth-card">
        <p className="eyebrow">YOUR CODE, WITH CONTEXT</p>
        <h1>{registering ? "Meet your codebase." : "Welcome back."}</h1>
        <p className="muted">
          {registering
            ? "Create your CodeBuddy account to start exploring."
            : "Pick up where you left off."}
        </p>
        <form onSubmit={submit}>
          {registering && (
            <label>
              Your name
              <input autoComplete="name" {...register("display_name")} />
              {errors.display_name && (
                <small>{errors.display_name.message}</small>
              )}
            </label>
          )}
          <label>
            Email address
            <input type="email" autoComplete="email" {...register("email")} />
            {errors.email && <small>{errors.email.message}</small>}
          </label>
          <label>
            Password
            <div className="password-field">
              <input
                type={visible ? "text" : "password"}
                autoComplete={registering ? "new-password" : "current-password"}
                {...register("password")}
              />
              <button
                type="button"
                onClick={() => setVisible(!visible)}
                aria-label={visible ? "Hide password" : "Show password"}
              >
                {visible ? "Hide" : "Show"}
              </button>
            </div>
            {errors.password && <small>{errors.password.message}</small>}
          </label>
          {registering && (
            <p className="muted small">
              Use at least 12 characters. Live AI requires your administrator to
              configure Gemini.
            </p>
          )}
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <button className="button solid" disabled={isSubmitting}>
            {isSubmitting
              ? "Please wait…"
              : registering
                ? "Create account"
                : "Sign in"}
          </button>
        </form>
        <p className="auth-switch">
          {registering ? "Already have an account?" : "New to CodeBuddy?"}{" "}
          <Link href={registering ? "/login" : "/register"}>
            {registering ? "Sign in" : "Create an account"}
          </Link>
        </p>
      </div>
      <p className="credit creator-credit">Powered by Malik Ismail Manzoor</p>
    </main>
  );
}
