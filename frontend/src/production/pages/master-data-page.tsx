import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import ResourcePage from "./resource-page"

const masters = [
  ["currencies", "Currencies"],
  ["units-of-measure", "Units"],
  ["tax-rates", "Tax rates"],
  ["payment-terms", "Payment terms"],
  ["delivery-terms", "Delivery terms"],
]

export default function MasterDataPage() {
  return (
    <Tabs defaultValue="currencies" className="flex flex-col gap-5">
      <TabsList className="h-auto flex-wrap justify-start">
        {masters.map(([value, label]) => <TabsTrigger key={value} value={value}>{label}</TabsTrigger>)}
      </TabsList>
      {masters.map(([value]) => <TabsContent key={value} value={value}><ResourcePage resourceKey={value} /></TabsContent>)}
    </Tabs>
  )
}
