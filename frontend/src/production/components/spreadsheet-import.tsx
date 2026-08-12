import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, FileSpreadsheet, Upload } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Field,
  FieldDescription,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { apiUpload } from "@/production/lib/api";

type SpreadsheetImportProps = {
  endpoint: string;
  label: string;
  templateName: string;
  headers: string[];
  required: string[];
  example: string[];
  queryKey: string[];
  note?: string;
};

function csvCell(value: string) {
  return `"${value.replaceAll('"', '""')}"`;
}

export default function SpreadsheetImport({
  endpoint,
  label,
  templateName,
  headers,
  required,
  example,
  queryKey,
  note,
}: SpreadsheetImportProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const mutation = useMutation({
    mutationFn: (selected: File) => {
      const body = new FormData();
      body.append("file", selected);
      return apiUpload<{ imported: number }>(endpoint, body);
    },
    onSuccess: async ({ imported }) => {
      await queryClient.invalidateQueries({ queryKey });
      setOpen(false);
      setFile(null);
      toast.success(`${imported} ${label} imported.`);
    },
  });

  function close() {
    setOpen(false);
    setFile(null);
    mutation.reset();
  }

  function downloadTemplate() {
    const csv = [headers, example]
      .map((row) => row.map(csvCell).join(","))
      .join("\r\n");
    const url = URL.createObjectURL(
      new Blob([`\uFEFF${csv}\r\n`], { type: "text/csv;charset=utf-8" }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `monika-${templateName}-import-template.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)}>
        <Upload data-icon="inline-start" />
        Import Excel / CSV
      </Button>
      <Dialog
        open={open}
        onOpenChange={(next) => (next ? setOpen(true) : close())}
      >
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Import previous {label}</DialogTitle>
            <DialogDescription>
              Upload Excel or CSV data exported from your current spreadsheet or
              Google Sheets.
            </DialogDescription>
          </DialogHeader>
          <Alert>
            <FileSpreadsheet />
            <AlertTitle>Safe, all-or-nothing import</AlertTitle>
            <AlertDescription>
              Up to 500 rows and 5 MB. If any row is invalid, nothing from the
              file is imported.
            </AlertDescription>
          </Alert>
          <Field>
            <FieldLabel htmlFor={`${templateName}-import-file`}>
              CSV or Excel file
            </FieldLabel>
            <Input
              id={`${templateName}-import-file`}
              type="file"
              accept=".csv,.xlsx"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
            <FieldDescription>
              Required columns: {required.join(", ")}.
            </FieldDescription>
          </Field>
          {note ? <p className="text-sm text-muted-foreground">{note}</p> : null}
          <Button
            variant="outline"
            className="justify-self-start"
            onClick={downloadTemplate}
          >
            <Download data-icon="inline-start" />
            Download CSV template
          </Button>
          {mutation.isError ? (
            <Alert variant="destructive">
              <AlertTitle>Data could not be imported</AlertTitle>
              <AlertDescription>{mutation.error.message}</AlertDescription>
            </Alert>
          ) : null}
          <DialogFooter>
            <Button variant="outline" onClick={close}>
              Cancel
            </Button>
            <Button
              onClick={() => file && mutation.mutate(file)}
              disabled={!file || mutation.isPending}
            >
              {mutation.isPending ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <Upload data-icon="inline-start" />
              )}
              {mutation.isPending ? "Importing…" : "Import data"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
