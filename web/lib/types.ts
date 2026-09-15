export type Source={title:string;url:string};
export type Lesson={id:string;title:string;minutes:number;body?:string;sources?:Source[]};
export type Module={id:string;title:string;level:string;description:string;lessons:Lesson[];sources:Source[];exercises?:Exercise[];number:number;status:string};
export type Track={id:string;title:string;description:string;status:string;modules:Module[];topics?:string[]};
export type Exercise={id:string;title:string;module_id:string;version:string;difficulty:string;mode:string;runner:string;minutes:number;statement:string;requirements:string[];starter:Record<string,string>;fixtures:{name:string;data:string;format:string}[];sources:Source[];objectives:string[];questions?:{id:string;prompt:string;options:string[]}[];status:string};
export type Progress={skills:{exercise_id:string;state:string;due:boolean;review_at:string}[];read_lessons:string[];recent_jobs:{id:string;exercise_id:string;status:string;created_at:string}[]};
