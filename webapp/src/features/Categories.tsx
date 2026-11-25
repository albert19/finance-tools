import { useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError, json, request } from "../api/client";
import type { Category } from "../api/types";
import { Field, Message } from "../design/ui";

export function Categories() {
  const { t } = useTranslation(),
    cache = useQueryClient();
  const [name, setName] = useState(""),
    [kind, setKind] = useState<"income" | "expense">("expense"),
    [error, setError] = useState("");
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => request<Category[]>("/categories"),
  });
  async function mutate(path: string, init: RequestInit) {
    setError("");
    try {
      await request(path, init);
      await cache.invalidateQueries({ queryKey: ["categories"] });
      return true;
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 409
          ? t("categoryInUse")
          : t("requestError"),
      );
      return false;
    }
  }
  function add(event: FormEvent) {
    event.preventDefault();
    void mutate("/categories", json("POST", { name: name.trim(), kind })).then(
      (created) => {
        if (created) setName("");
      },
    );
  }
  return (
    <section className="category-panel" aria-labelledby="category-settings">
      <h2 id="category-settings">{t("categories")}</h2>
      <p>{t("categorySettingsHint")}</p>
      {error && <Message>{error}</Message>}
      {categories.isError && (
        <Message retry={() => void categories.refetch()}>
          {t("loadError")}
        </Message>
      )}
      <div className="category-list">
        {(categories.data ?? []).map((category) => (
          <div className="category-row" key={category.id}>
            <div>
              <strong>{category.name}</strong>
              <small>
                {t(category.kind)}
                {category.archived ? ` · ${t("archived")}` : ""}
              </small>
            </div>
            <div>
              <button
                className="text-button"
                onClick={() => {
                  const next = prompt(t("name"), category.name);
                  if (next?.trim())
                    void mutate(
                      `/categories/${category.id}`,
                      json("PATCH", { name: next.trim() }),
                    );
                }}
              >
                {t("edit")}
              </button>
              <button
                className="text-button"
                onClick={() =>
                  void mutate(
                    `/categories/${category.id}`,
                    json("PATCH", { archived: !category.archived }),
                  )
                }
              >
                {t(category.archived ? "unarchive" : "archive")}
              </button>
              <button
                className="text-button destructive"
                onClick={() => {
                  if (confirm(t("confirmDelete")))
                    void mutate(`/categories/${category.id}`, {
                      method: "DELETE",
                    });
                }}
              >
                {t("delete")}
              </button>
            </div>
          </div>
        ))}
      </div>
      <form className="category-form" onSubmit={add}>
        <Field label={t("name")}>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <Field label={t("type")}>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value as typeof kind)}
          >
            <option value="expense">{t("expense")}</option>
            <option value="income">{t("income")}</option>
          </select>
        </Field>
        <button className="primary">{t("addCategory")}</button>
      </form>
      {!categories.data?.length && (
        <button
          className="text-button"
          onClick={() =>
            void mutate("/categories/defaults", { method: "POST" })
          }
        >
          {t("defaults")}
        </button>
      )}
    </section>
  );
}
