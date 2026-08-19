import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it } from "vitest"

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"

describe("SheetContent", () => {
  afterEach(() => cleanup())

  it("uses a padded full-width mobile layout with an overridable desktop width", () => {
    render(
      <Sheet open>
        <SheetContent className="sm:max-w-3xl">
          <SheetHeader>
            <SheetTitle>New customer</SheetTitle>
            <SheetDescription>Customer form</SheetDescription>
          </SheetHeader>
        </SheetContent>
      </Sheet>,
    )

    expect(screen.getByRole("dialog", { name: "New customer" })).toHaveClass(
      "w-full",
      "p-4",
      "sm:p-6",
      "sm:max-w-3xl",
    )
  })
})
