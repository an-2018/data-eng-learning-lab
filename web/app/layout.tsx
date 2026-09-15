import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {title:'Graphlab — Learn by building',description:'A learning workspace for ontology engineering, knowledge graphs, and Apache Spark.',icons:{icon:'/favicon.svg'}};
export default function Layout({children}:{children:React.ReactNode}) {return <html lang="en"><body>{children}</body></html>}
