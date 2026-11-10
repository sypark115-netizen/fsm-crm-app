import { redirect } from "next/navigation";
import { Workspace } from "@/components/workspace/Workspace";
import { currentUser } from "@/lib/server/auth";

export default async function Home() {
  if (!(await currentUser())) redirect("/login");
  return <Workspace />;
}
