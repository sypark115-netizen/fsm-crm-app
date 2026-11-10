import { redirect } from "next/navigation";
import { currentUser } from "@/lib/server/auth";
import { countUsers } from "@/lib/server/repo";
import { LoginForm } from "./LoginForm";

export default async function LoginPage() {
  if (await currentUser()) redirect("/");
  const firstUser = countUsers() === 0;
  return <LoginForm firstUser={firstUser} signupOpen={firstUser || Boolean(process.env.EXI_INVITE_CODE)} />;
}
