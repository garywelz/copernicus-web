"use client"

import * as React from "react"
import { Loader2 } from 'lucide-react'

export default function Loading() {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Loader2 className="h-12 w-12 animate-spin text-gray-400" />
      <p className="mt-4 text-gray-500">Loading episodes...</p>
    </div>
  )
} 