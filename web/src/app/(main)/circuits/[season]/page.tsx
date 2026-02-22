import { redirect } from "next/navigation";

// Redirect old season-based URLs to the main circuits page
export default function CircuitsSeasonPage() {
  redirect("/circuits");
}
