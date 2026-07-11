"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent, type ReactNode } from "react";

import { CsvUpload, type CsvSelection } from "@/components/forms/csv-upload";
import { ErrorState } from "@/components/states";
import { siteSiftApi, type SiteSiftApi } from "@/lib/api";
import type { CreateProjectRequest, ProjectType } from "@/types/api";

export interface ProjectFormValues {
  name: string;
  project_type: string;
  target_capacity_mw: string;
  minimum_acres: string;
  target_state: string;
  maximum_flood_overlap_percent: string;
  maximum_wetland_overlap_percent: string;
  maximum_road_distance_miles: string;
  notes: string;
}

const initialValues: ProjectFormValues = {
  name: "",
  project_type: "",
  target_capacity_mw: "",
  minimum_acres: "",
  target_state: "",
  maximum_flood_overlap_percent: "5",
  maximum_wetland_overlap_percent: "10",
  maximum_road_distance_miles: "2",
  notes: "",
};

export function validateProjectForm(values: ProjectFormValues): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!values.name.trim()) errors.name = "Project name is required.";
  if (!values.project_type) errors.project_type = "Project type is required.";
  if (!values.target_state.trim()) errors.target_state = "Target state is required.";

  const positiveFields: Array<[keyof ProjectFormValues, string]> = [
    ["target_capacity_mw", "Target capacity"],
    ["minimum_acres", "Minimum acreage"],
    ["maximum_road_distance_miles", "Maximum road distance"],
  ];
  positiveFields.forEach(([field, label]) => {
    const value = Number(values[field]);
    if (!values[field]) errors[field] = `${label} is required.`;
    else if (!Number.isFinite(value) || value <= 0) errors[field] = `${label} must be greater than 0.`;
  });

  const percentFields: Array<[keyof ProjectFormValues, string]> = [
    ["maximum_flood_overlap_percent", "Maximum flood overlap"],
    ["maximum_wetland_overlap_percent", "Maximum wetland overlap"],
  ];
  percentFields.forEach(([field, label]) => {
    const value = Number(values[field]);
    if (!values[field]) errors[field] = `${label} is required.`;
    else if (!Number.isFinite(value) || value < 0 || value > 100) errors[field] = `${label} must be between 0 and 100.`;
  });
  return errors;
}

type ScreeningFormApi = Pick<SiteSiftApi, "createProject" | "importCandidateSites" | "runScreening">;

export function NewScreeningForm({ api = siteSiftApi }: { api?: ScreeningFormApi }) {
  const router = useRouter();
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [selection, setSelection] = useState<CsvSelection | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const update = (field: keyof ProjectFormValues, value: string) => {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => {
      const next = { ...current };
      delete next[field];
      return next;
    });
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors = validateProjectForm(values);
    if (!selection) nextErrors.csv = "A candidate-site CSV is required.";
    else if (selection.result.rows.length === 0) nextErrors.csv = "The CSV must contain at least one data row.";
    else if (selection.result.issues.length > 0) nextErrors.csv = "Resolve CSV validation issues before screening.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0 || !selection) return;

    const request: CreateProjectRequest = {
      name: values.name.trim(),
      project_type: values.project_type as ProjectType,
      target_capacity_mw: Number(values.target_capacity_mw),
      minimum_acres: Number(values.minimum_acres),
      target_state: values.target_state.trim().toUpperCase(),
      screening_criteria: {
        maximum_flood_overlap_percent: Number(values.maximum_flood_overlap_percent),
        maximum_wetland_overlap_percent: Number(values.maximum_wetland_overlap_percent),
        maximum_road_distance_miles: Number(values.maximum_road_distance_miles),
      },
      notes: values.notes.trim() || null,
    };

    setSubmitting(true);
    setSubmitError(null);
    try {
      const project = await api.createProject(request);
      await api.importCandidateSites(project.id, selection.file);
      await api.runScreening(project.id);
      router.push(`/projects/${project.id}/results`);
    } catch (caught) {
      setSubmitError(caught instanceof Error ? caught.message : "The screening could not be created.");
      setSubmitting(false);
    }
  };

  return (
    <form noValidate onSubmit={(event) => void submit(event)} className="space-y-6">
      {Object.keys(errors).length > 0 ? (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <p className="font-bold">Review {Object.keys(errors).length} highlighted field{Object.keys(errors).length === 1 ? "" : "s"}.</p>
        </div>
      ) : null}
      {submitError ? <ErrorState title="Screening could not start" message={submitError} /> : null}

      <FormSection number="01" title="Project details" description="Define the development target used to evaluate every candidate.">
        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="Project name" name="name" error={errors.name} className="sm:col-span-2">
            <input id="name" name="name" value={values.name} onChange={(event) => update("name", event.target.value)} aria-invalid={Boolean(errors.name)} aria-describedby={errors.name ? "name-error" : undefined} className={inputClass} placeholder="Hudson Valley Community Solar" />
          </Field>
          <Field label="Project type" name="project_type" error={errors.project_type}>
            <select id="project_type" name="project_type" value={values.project_type} onChange={(event) => update("project_type", event.target.value)} aria-invalid={Boolean(errors.project_type)} aria-describedby={errors.project_type ? "project_type-error" : undefined} className={inputClass}>
              <option value="">Select a project type</option>
              <option value="solar">Solar</option>
              <option value="battery_storage">Battery storage</option>
              <option value="data_center">Data center</option>
              <option value="ev_charging">EV charging</option>
              <option value="other">Other power infrastructure</option>
            </select>
          </Field>
          <Field label="Target state" name="target_state" error={errors.target_state} hint="Two-letter abbreviation or state name">
            <input id="target_state" name="target_state" value={values.target_state} onChange={(event) => update("target_state", event.target.value)} aria-invalid={Boolean(errors.target_state)} aria-describedby={errors.target_state ? "target_state-error" : undefined} className={inputClass} placeholder="NY" />
          </Field>
          <Field label="Target capacity" name="target_capacity_mw" error={errors.target_capacity_mw} suffix="MW">
            <input id="target_capacity_mw" name="target_capacity_mw" type="number" min="0" step="0.1" value={values.target_capacity_mw} onChange={(event) => update("target_capacity_mw", event.target.value)} aria-invalid={Boolean(errors.target_capacity_mw)} aria-describedby={errors.target_capacity_mw ? "target_capacity_mw-error" : undefined} className={inputClass} placeholder="5" />
          </Field>
          <Field label="Minimum acreage" name="minimum_acres" error={errors.minimum_acres} suffix="acres">
            <input id="minimum_acres" name="minimum_acres" type="number" min="0" step="0.1" value={values.minimum_acres} onChange={(event) => update("minimum_acres", event.target.value)} aria-invalid={Boolean(errors.minimum_acres)} aria-describedby={errors.minimum_acres ? "minimum_acres-error" : undefined} className={inputClass} placeholder="25" />
          </Field>
          <Field label="Notes" name="notes" className="sm:col-span-2" hint="Optional context for reviewers">
            <textarea id="notes" name="notes" rows={3} value={values.notes} onChange={(event) => update("notes", event.target.value)} className={inputClass} placeholder="Known constraints, timeline, or site-control context" />
          </Field>
        </div>
      </FormSection>

      <FormSection number="02" title="Screening thresholds" description="Set the deterministic limits applied to every uploaded row.">
        <div className="grid gap-5 sm:grid-cols-3">
          <Field label="Maximum flood overlap" name="maximum_flood_overlap_percent" error={errors.maximum_flood_overlap_percent} suffix="%">
            <input id="maximum_flood_overlap_percent" name="maximum_flood_overlap_percent" type="number" min="0" max="100" step="0.1" value={values.maximum_flood_overlap_percent} onChange={(event) => update("maximum_flood_overlap_percent", event.target.value)} aria-invalid={Boolean(errors.maximum_flood_overlap_percent)} className={inputClass} />
          </Field>
          <Field label="Maximum wetland overlap" name="maximum_wetland_overlap_percent" error={errors.maximum_wetland_overlap_percent} suffix="%">
            <input id="maximum_wetland_overlap_percent" name="maximum_wetland_overlap_percent" type="number" min="0" max="100" step="0.1" value={values.maximum_wetland_overlap_percent} onChange={(event) => update("maximum_wetland_overlap_percent", event.target.value)} aria-invalid={Boolean(errors.maximum_wetland_overlap_percent)} className={inputClass} />
          </Field>
          <Field label="Maximum road distance" name="maximum_road_distance_miles" error={errors.maximum_road_distance_miles} suffix="miles">
            <input id="maximum_road_distance_miles" name="maximum_road_distance_miles" type="number" min="0" step="0.1" value={values.maximum_road_distance_miles} onChange={(event) => update("maximum_road_distance_miles", event.target.value)} aria-invalid={Boolean(errors.maximum_road_distance_miles)} className={inputClass} />
          </Field>
        </div>
      </FormSection>

      <FormSection number="03" title="Candidate-site CSV" description="Preview and validate locally before any rows are imported.">
        <CsvUpload selection={selection} onChange={(next) => { setSelection(next); setErrors((current) => { const copy = { ...current }; delete copy.csv; return copy; }); }} />
        {errors.csv ? <p id="csv-error" role="alert" className="mt-3 text-sm font-semibold text-red-700">{errors.csv}</p> : null}
      </FormSection>

      <div className="flex flex-col-reverse gap-3 border-t border-slate-200 pt-6 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs leading-5 text-slate-500">Screening uses transparent deterministic rules. Document analysis is a later, separate step.</p>
        <button type="submit" disabled={submitting} className="rounded-md bg-forest px-5 py-3 text-sm font-bold text-white shadow-sm hover:bg-[#123e39] disabled:cursor-wait disabled:opacity-60">
          {submitting ? "Running screening…" : "Run Screening"}
        </button>
      </div>
    </form>
  );
}

const inputClass = "w-full rounded-md border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-ink shadow-sm placeholder:text-slate-400 hover:border-slate-400 focus:border-forest";

function FormSection({ number, title, description, children }: { number: string; title: string; description: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex gap-4 border-b border-slate-200 px-5 py-5 sm:px-6">
        <span className="font-mono text-xs font-bold text-forest">{number}</span>
        <div><h2 className="font-bold text-ink">{title}</h2><p className="mt-1 text-sm text-slate-500">{description}</p></div>
      </div>
      <div className="p-5 sm:p-6">{children}</div>
    </section>
  );
}

function Field({ label, name, error, hint, suffix, className = "", children }: { label: string; name: string; error?: string; hint?: string; suffix?: string; className?: string; children: ReactNode }) {
  return (
    <div className={className}>
      <div className="mb-2 flex items-baseline justify-between gap-3"><label htmlFor={name} className="text-sm font-bold text-slate-700">{label}</label>{suffix ? <span className="text-xs text-slate-400">{suffix}</span> : null}</div>
      {children}
      {error ? <p id={`${name}-error`} className="mt-1.5 text-xs font-semibold text-red-700">{error}</p> : hint ? <p className="mt-1.5 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}
