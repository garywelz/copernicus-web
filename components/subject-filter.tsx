"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"

interface SubjectFilterProps {
  activeSubject: string
  onSubjectChange: (subject: string) => void
}

export default function SubjectFilter({ activeSubject, onSubjectChange }: SubjectFilterProps) {
  const subjects = ["News", "Biology", "Chemistry", "Computer Science", "Mathematics", "Physics"]

  return (
    <div className="flex flex-wrap gap-3">
      {subjects.map((subject) => (
        <Button
          key={subject}
          variant={activeSubject === subject ? "default" : "outline"}
          className={`rounded-full ${activeSubject === subject ? "bg-green-600 hover:bg-green-700" : "bg-gray-100 hover:bg-gray-200 border-none"}`}
          onClick={() => onSubjectChange(subject)}
        >
          {subject}
        </Button>
      ))}
    </div>
  )
} 