import { Link } from "react-router"

export function NotFoundPage() {
  return (
    <section className="flex flex-col gap-2">
      <h1 className="text-xl font-semibold">Page not found</h1>
      <Link to="/" className="underline">
        Go to your episodes
      </Link>
    </section>
  )
}
