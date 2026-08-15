"use client";

import { Menu } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { MobileSearchInput } from "@/components/search/mobile-search-input";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";

export type NavLink = {
	href: string;
	label: string;
};

export function Navbar({ links }: { links: NavLink[] }) {
	const [open, setOpen] = useState(false);

	return (
		<>
			<Sheet open={open} onOpenChange={setOpen}>
				<SheetTrigger asChild>
					<button
						type="button"
						aria-label="Open menu"
						className="-order-1 rounded-full p-2 text-white/70 transition-colors hover:bg-secondary hover:text-white lg:hidden"
					>
						<Menu className="h-6 w-6" />
					</button>
				</SheetTrigger>
				<SheetContent side="left" className="gap-0 overflow-y-auto border-white/10 bg-neutral-950 p-6">
					<SheetTitle className="sr-only">Menu</SheetTitle>
					<div className="mt-6">
						<MobileSearchInput onNavigate={() => setOpen(false)} />
					</div>
					<nav className="mt-6 flex flex-col gap-1">
						{links.map((link) => (
							<Link
								key={link.href}
								href={link.href}
								onClick={() => setOpen(false)}
								className="rounded-xl px-3 py-3.5 text-lg font-semibold tracking-tight text-foreground transition-colors hover:bg-secondary"
							>
								{link.label}
							</Link>
						))}
					</nav>
				</SheetContent>
			</Sheet>
			<nav className="hidden items-center gap-7 lg:absolute lg:left-1/2 lg:top-1/2 lg:flex lg:-translate-x-1/2 lg:-translate-y-1/2">
				{links.map((link) => (
					<Link
						key={link.href}
						href={link.href}
						className="whitespace-nowrap text-xs font-semibold uppercase tracking-[0.11em] text-muted-foreground transition-colors hover:text-lime-300"
					>
						{link.label}
					</Link>
				))}
			</nav>
		</>
	);
}
