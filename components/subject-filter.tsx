"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"

interface SubjectFilterProps {
  activeSubject: string
  onSubjectChange: (subject: string) => void
}

export default function SubjectFilter({ activeSubject, onSubjectChange }: SubjectFilterProps) {
<<<<<<< HEAD
  const subjects = ["News", "Biology", "Chemistry", "ComputerScience", "Mathematics", "Physics"]

  const getDisplayName = (subject: string) => {
    return subject === "ComputerScience" ? "Computer Science" : subject
  }
=======
  const subjects = ["News", "Biology", "Chemistry", "Computer Science", "Mathematics", "Physics"]
>>>>>>> 7c13d53b1e209c067ff2ff680d00fe9aec2fd3bb

  return (
    <div className="flex flex-wrap gap-3">
      {subjects.map((subject) => (
        <Button
          key={subject}
          variant={activeSubject === subject ? "default" : "outline"}
          className={`rounded-full ${activeSubject === subject ? "bg-green-600 hover:bg-green-700" : "bg-gray-100 hover:bg-gray-200 border-none"}`}
          onClick={() => onSubjectChange(subject)}
        >
<<<<<<< HEAD
          {getDisplayName(subject)}
=======
          {subject}
>>>>>>> 7c13d53b1e209c067ff2ff680d00fe9aec2fd3bb
        </Button>
      ))}
    </div>
  )
} 